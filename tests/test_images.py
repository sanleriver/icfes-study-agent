import pytest

from src.data.images import IMAGES_DIR, image_source
from src.data.loader import load_questions, validate_image_references
from src.models import Question, Section

QUESTION_DATA = {
    "id": "RQ-003",
    "section": Section.RAZONAMIENTO_CUANTITATIVO,
    "topic": "Interpretación de gráficas",
    "statement": "La gráfica muestra las ventas.",
    "options": {"A": "100", "B": "103", "C": "110", "D": "93"},
    "correct_option": "B",
}


class TestQuestionImagen:
    def test_acepta_ruta_local(self):
        q = Question.model_validate({**QUESTION_DATA, "statement_image": "RQ-003.png"})
        assert q.statement_image == "RQ-003.png"

    def test_acepta_url(self):
        url = "https://example.com/grafica.png"
        q = Question.model_validate({**QUESTION_DATA, "statement_image": url})
        assert q.statement_image == url

    def test_sin_imagen_es_none(self):
        q = Question.model_validate(QUESTION_DATA)
        assert q.statement_image is None

    def test_rechaza_valor_vacio(self):
        with pytest.raises(Exception):
            Question.model_validate({**QUESTION_DATA, "statement_image": "   "})


class TestImageSource:
    def test_none_cuando_no_hay_imagen(self):
        q = Question.model_validate(QUESTION_DATA)
        assert image_source(q) is None

    def test_resuelve_ruta_local(self):
        q = Question.model_validate({**QUESTION_DATA, "statement_image": "RQ-003.png"})
        assert image_source(q) == IMAGES_DIR / "RQ-003.png"

    def test_devuelve_url_tal_cual(self):
        url = "https://example.com/grafica.png"
        q = Question.model_validate({**QUESTION_DATA, "statement_image": url})
        assert image_source(q) == url


class TestValidateImageReferences:
    def test_banco_real_tiene_imagenes_validas(self):
        questions = load_questions()
        sources = validate_image_references(questions)
        assert all(source.exists() for source in sources)

    def test_detecta_ruta_inexistente(self):
        q = Question.model_validate(
            {**QUESTION_DATA, "statement_image": "no-existe.png"}
        )
        with pytest.raises(FileNotFoundError):
            validate_image_references([q])

    def test_ignora_urls(self):
        url = "https://example.com/grafica.png"
        q = Question.model_validate({**QUESTION_DATA, "statement_image": url})
        assert validate_image_references([q]) == []