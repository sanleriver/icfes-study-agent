import time
import urllib.request
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.core.feedback import fallback_feedback
from src.data.images import image_source
from src.models import EvaluationResult, Feedback, Question

from .base import FeedbackProvider

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class FeedbackContent(BaseModel):
    """Esquema JSON estricto que debe devolver el modelo.

    `question_id` se completa después con el id de la pregunta real, ya que el
    modelo no conoce los ids internos del banco.
    """

    explanation: str
    error_analysis: str
    positive_reinforcement: str
    suggestion_topic: str


class GeminiFeedbackProvider(FeedbackProvider):
    """Proveedor LLM con Gemini (SDK `google-genai`).

    Llama a `generate_content` con salida JSON validada con Pydantic, reintenta
    hasta 3 veces con *exponential backoff* y, si persiste el fallo o la salida
    no es válida, cae en `fallback_feedback` sin romper la sesión.

    Si la pregunta tiene `statement_image`, la imagen se incluye como parte de
    entrada de visión: bytes locales (resueltos con `image_source`) o una URL
    descargada.
    """

    DEFAULT_MODEL = "gemini-3.5-flash"
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0
    DOWNLOAD_TIMEOUT = 10

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: genai.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client if client is not None else genai.Client(api_key=api_key)

    def generate_feedback(
        self,
        question: Question,
        result: EvaluationResult,
    ) -> Feedback:
        contents = self._build_contents(question, result)
        try:
            text = self._request_with_retry(contents)
            return self._parse_response(text, question)
        except Exception:
            return fallback_feedback(question, result)

    def _build_contents(
        self,
        question: Question,
        result: EvaluationResult,
    ) -> str | list:
        """Arma los `parts` de entrada: texto + imagen de visión si existe."""
        prompt = self._build_prompt(question, result)
        source = image_source(question)
        if source is None:
            return prompt
        if isinstance(source, Path):
            image_bytes = source.read_bytes()
            mime_type = _MIME_BY_EXT.get(
                source.suffix.lower(), "application/octet-stream"
            )
        else:
            image_bytes, mime_type = self._download_image(source)
        return [prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)]

    def _build_prompt(
        self,
        question: Question,
        result: EvaluationResult,
    ) -> str:
        options = "\n".join(f"{k}) {v}" for k, v in question.options.items())
        return (
            "Eres un tutor pedagógico del ICFES Saber Pro. Genera "
            "retroalimentación en español para la siguiente pregunta respondida "
            "incorrectamente, en JSON estricto con los campos: explanation "
            "(explicación conceptual del tema), error_analysis (por qué el "
            "distractor elegido es incorrecto y qué debió considerarse), "
            "positive_reinforcement (refuerzo positivo breve) y "
            "suggestion_topic (tema para repasar).\n\n"
            f"Pregunta ({question.topic}): {question.statement}\n"
            f"Opciones:\n{options}\n"
            f"Opción elegida: {result.selected_option}\n"
            f"Opción correcta: {result.correct_option}\n"
            f"Puntos clave: {', '.join(question.key_points) or 'no disponibles'}\n"
            "Si la pregunta incluye una imagen, analízala junto al texto."
        )

    def _download_image(self, url: str) -> tuple[bytes, str]:
        """Descarga una imagen remota y devuelve (bytes, mime_type)."""
        with urllib.request.urlopen(url, timeout=self.DOWNLOAD_TIMEOUT) as response:
            data = response.read()
            mime_type = response.headers.get_content_type() or "image/png"
        return data, mime_type

    def _request_with_retry(self, contents: str | list) -> str:
        """Invoca a Gemini con reintentos y *exponential backoff*."""
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=FeedbackContent,
                    ),
                )
                if response.text is None:
                    raise ValueError("La respuesta de Gemini no contiene texto")
                return response.text
            except Exception as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BASE_DELAY * (2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Falló la llamada a Gemini")

    def _parse_response(self, text: str, question: Question) -> Feedback:
        """Valida el JSON devuelto con Pydantic y arma el `Feedback`."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```")
            cleaned = cleaned.removesuffix("```").strip()
        content = FeedbackContent.model_validate_json(cleaned)
        return Feedback(
            question_id=question.id,
            explanation=content.explanation,
            error_analysis=content.error_analysis,
            positive_reinforcement=content.positive_reinforcement,
            suggestion_topic=content.suggestion_topic,
        )