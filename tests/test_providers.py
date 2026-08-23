import tempfile
import types as pytypes
import unittest.mock as mock
from pathlib import Path

import pytest

from src.core.feedback import fallback_feedback
from src.models import EvaluationResult, Feedback, Question, Section
from src.providers import (
    FeedbackProvider,
    GeminiFeedbackProvider,
    MockFeedbackProvider,
    create_feedback_provider,
)
from src.providers.gemini import FeedbackContent

SECTION = Section.RAZONAMIENTO_CUANTITATIVO
QUESTION = Question(
    id="RQ-001",
    section=SECTION,
    topic="Probabilidad",
    statement="¿Cuál es la probabilidad de sacar una bola roja?",
    options={"A": "1/3", "B": "1/2", "C": "1/4", "D": "1/6"},
    correct_option="A",
    key_points=["Regla de Laplace"],
)
RESULT = EvaluationResult(
    question_id="RQ-001",
    selected_option="B",
    correct_option="A",
    is_correct=False,
)
VALID_JSON = (
    '{"explanation":"Explicación","error_analysis":"Error",'
    '"positive_reinforcement":"Refuerzo","suggestion_topic":"Probabilidad"}'
)


class FakeGeminiClient:
    """Cliente fake de `google.genai` para probar sin API key."""

    def __init__(self, text: str | None = None, failures: int = 0) -> None:
        self._text = text
        self._failures = failures
        self.calls: list[tuple] = []
        self.models = pytypes.SimpleNamespace(generate_content=self._generate_content)

    def _generate_content(self, model, contents, config):
        self.calls.append((model, contents, config))
        if self._failures > 0:
            self._failures -= 1
            raise TimeoutError("fallo simulado")
        return pytypes.SimpleNamespace(text=self._text)


def _gemini_provider(client=None, **kwargs) -> GeminiFeedbackProvider:
    provider = GeminiFeedbackProvider(
        api_key="fake-key", client=client or FakeGeminiClient(text=VALID_JSON)
    )
    provider.RETRY_BASE_DELAY = 0
    return provider


class TestContrato:
    def test_feedback_provider_es_abstracto(self):
        with pytest.raises(TypeError):
            FeedbackProvider()

    def test_mock_y_gemini_cumplen_el_contrato(self):
        assert isinstance(MockFeedbackProvider(), FeedbackProvider)
        assert isinstance(GeminiFeedbackProvider(api_key="fake"), FeedbackProvider)

    def test_generate_feedback_devuelve_feedback(self):
        provider = _gemini_provider()
        fb = provider.generate_feedback(QUESTION, RESULT)
        assert isinstance(fb, Feedback)


class TestMockProvider:
    def test_es_determinista_y_usa_puntos_clave(self):
        provider = MockFeedbackProvider()
        first = provider.generate_feedback(QUESTION, RESULT)
        second = provider.generate_feedback(QUESTION, RESULT)
        assert first == second
        assert first.question_id == "RQ-001"
        assert "Laplace" in first.explanation
        assert first.suggestion_topic == "Probabilidad"
        assert "B" in first.error_analysis

    def test_delega_en_fallback(self):
        fb = MockFeedbackProvider().generate_feedback(QUESTION, RESULT)
        assert fb == fallback_feedback(QUESTION, RESULT)


class TestFallback:
    def test_feedback_determinista_sin_puntos_clave(self):
        q = QUESTION.model_copy(update={"key_points": []})
        fb = fallback_feedback(q, RESULT)
        assert "Probabilidad" in fb.explanation


class TestGeminiProvider:
    def test_parsea_json_valido_en_feedback(self):
        provider = _gemini_provider()
        fb = provider.generate_feedback(QUESTION, RESULT)
        assert fb.question_id == "RQ-001"
        assert fb.explanation == "Explicación"
        assert fb.suggestion_topic == "Probabilidad"

    def test_envia_schema_json_a_gemini(self):
        provider = _gemini_provider()
        provider.generate_feedback(QUESTION, RESULT)
        _, _, config = provider.client.calls[0]
        assert config.response_mime_type == "application/json"
        assert config.response_schema is FeedbackContent

    def test_acepta_json_con_fences_de_markdown(self):
        text = f"```json\n{VALID_JSON}\n```"
        provider = _gemini_provider(client=FakeGeminiClient(text=text))
        fb = provider.generate_feedback(QUESTION, RESULT)
        assert fb.explanation == "Explicación"

    def test_reintenta_3_veces_y_cae_a_fallback(self):
        client = FakeGeminiClient(failures=5)
        provider = _gemini_provider(client=client)
        fb = provider.generate_feedback(QUESTION, RESULT)
        assert len(client.calls) == GeminiFeedbackProvider.MAX_RETRIES
        assert fb == fallback_feedback(QUESTION, RESULT)

    def test_json_invalido_cae_a_fallback(self):
        provider = _gemini_provider(client=FakeGeminiClient(text="no es json"))
        fb = provider.generate_feedback(QUESTION, RESULT)
        assert fb == fallback_feedback(QUESTION, RESULT)

    def test_respuesta_sin_texto_cae_a_fallback(self):
        client = FakeGeminiClient(text=None)
        provider = _gemini_provider(client=client)
        fb = provider.generate_feedback(QUESTION, RESULT)
        assert fb == fallback_feedback(QUESTION, RESULT)


class TestGeminiVision:
    def test_imagen_local_se_incluye_como_inline_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grafica.png"
            raw = b"\x89PNG\r\n\x1a\n" + b"datos"
            path.write_bytes(raw)
            q = QUESTION.model_copy(update={"statement_image": str(path)})
            provider = _gemini_provider()
            provider.generate_feedback(q, RESULT)
            model, contents, _ = provider.client.calls[0]
            assert model == provider.model
            assert isinstance(contents, list) and len(contents) == 2
            part = contents[1]
            assert part.inline_data.mime_type == "image/png"
            assert part.inline_data.data == raw

    def test_imagen_url_se_descarga_como_inline_data(self):
        q = QUESTION.model_copy(
            update={"statement_image": "https://example.com/grafica.png"}
        )
        provider = _gemini_provider()
        with mock.patch("urllib.request.urlopen") as urlopen:
            response = mock.MagicMock()
            response.read.return_value = b"urldata"
            response.headers.get_content_type.return_value = "image/png"
            urlopen.return_value.__enter__.return_value = response
            provider.generate_feedback(q, RESULT)
        _, contents, _ = provider.client.calls[0]
        assert contents[1].inline_data.mime_type == "image/png"
        assert contents[1].inline_data.data == b"urldata"

    def test_sin_imagen_envia_solo_texto(self):
        provider = _gemini_provider()
        provider.generate_feedback(QUESTION, RESULT)
        _, contents, _ = provider.client.calls[0]
        assert isinstance(contents, str)
        assert "RQ-001" in contents or "Probabilidad" in contents


class TestFactory:
    def test_mock_por_defecto(self):
        from src.config import Settings

        provider = create_feedback_provider(Settings(feedback_provider="mock"))
        assert isinstance(provider, MockFeedbackProvider)

    def test_gemini_sin_clave_lanza_error(self):
        from src.config import Settings

        with pytest.raises(ValueError):
            create_feedback_provider(
                Settings(feedback_provider="gemini", gemini_api_key="")
            )

    def test_gemini_usa_modelo_de_la_config(self):
        from src.config import Settings

        provider = create_feedback_provider(
            Settings(
                feedback_provider="gemini",
                gemini_api_key="clave",
                gemini_model="gemini-2.0-flash",
            )
        )
        assert isinstance(provider, GeminiFeedbackProvider)
        assert provider.model == "gemini-2.0-flash"