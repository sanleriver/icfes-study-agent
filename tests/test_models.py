import pytest
from pydantic import ValidationError

from src.models import AnswerRecord, Question, Section, SessionState

QUESTION_DATA = {
    "id": "LC-001",
    "section": Section.LECTURA_CRITICA,
    "topic": "Comprensión de textos",
    "statement": "¿Cuál es la idea principal del texto?",
    "options": {"A": "Primera", "B": "Segunda", "C": "Tercera", "D": "Cuarta"},
    "correct_option": "B",
    "key_points": ["Identificar la tesis."],
}


class TestSection:
    def test_label_para_cada_seccion(self):
        assert Section.LECTURA_CRITICA.label == "Lectura Crítica"
        assert Section.RAZONAMIENTO_CUANTITATIVO.label == "Razonamiento Cuantitativo"
        assert Section.COMPETENCIAS_CIUDADANAS.label == "Competencias Ciudadanas"
        assert Section.COMUNICACION_ESCRITA.label == "Comunicación Escrita"
        assert Section.INGLES.label == "Inglés"

    def test_total_secciones(self):
        assert len(Section) == 5


class TestQuestion:
    def test_question_valida(self):
        q = Question.model_validate(QUESTION_DATA)
        assert q.section is Section.LECTURA_CRITICA

    def test_rechaza_opciones_incompletas(self):
        data = dict(QUESTION_DATA)
        data["options"] = {"A": "x", "B": "y"}
        with pytest.raises(ValidationError):
            Question.model_validate(data)

    def test_rechaza_opcion_correcta_fuera_de_rango(self):
        data = dict(QUESTION_DATA)
        data["correct_option"] = "E"
        with pytest.raises(ValidationError):
            Question.model_validate(data)


class TestAnswerRecord:
    def test_rechaza_opcion_invalida(self):
        with pytest.raises(ValidationError):
            AnswerRecord(question_id="LC-001", selected_option="Z")


class TestSessionState:
    def test_defaults(self):
        state = SessionState()
        assert state.num_questions == 10
        assert state.answers == []
        assert state.section is None

    def test_rechaza_num_questions_cero(self):
        with pytest.raises(ValidationError):
            SessionState(num_questions=0)

    def test_answers_acumulan_con_reducer(self):
        state = SessionState()
        state.answers = [AnswerRecord(question_id="LC-001", selected_option="A")]
        state.answers = state.answers + [
            AnswerRecord(question_id="LC-001", selected_option="B")
        ]
        assert len(state.answers) == 2