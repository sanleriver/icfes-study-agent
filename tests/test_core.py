import pytest

from src.core.evaluation import build_summary, evaluate_session, incorrect_question_ids
from src.models import AnswerRecord, Question, Section

SECTION = Section.LECTURA_CRITICA
QUESTIONS = [
    Question(
        id="LC-001",
        section=SECTION,
        topic="Comprensión de textos",
        statement="Pregunta uno",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_option="A",
    ),
    Question(
        id="LC-002",
        section=SECTION,
        topic="Inferencia",
        statement="Pregunta dos",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_option="B",
    ),
    Question(
        id="LC-003",
        section=SECTION,
        topic="Comprensión de textos",
        statement="Pregunta tres",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_option="C",
    ),
]


def test_evalua_correcta_e_incorrecta():
    answers = [
        AnswerRecord(question_id="LC-001", selected_option="A"),
        AnswerRecord(question_id="LC-002", selected_option="A"),
    ]
    results = evaluate_session(QUESTIONS, answers)
    assert [r.is_correct for r in results] == [True, False]
    assert results[0].correct_option == "A"
    assert results[1].selected_option == "A"


def test_incorrect_question_ids_solo_incorrectas():
    answers = [
        AnswerRecord(question_id="LC-001", selected_option="A"),
        AnswerRecord(question_id="LC-002", selected_option="A"),
        AnswerRecord(question_id="LC-003", selected_option="C"),
    ]
    results = evaluate_session(QUESTIONS, answers)
    assert incorrect_question_ids(results) == ["LC-002"]


def test_respuesta_de_pregunta_desconocida_lanza_error():
    with pytest.raises(ValueError):
        evaluate_session(QUESTIONS, [AnswerRecord(question_id="XX", selected_option="A")])


def test_build_summary_puntuacion_y_por_tema():
    answers = [
        AnswerRecord(question_id="LC-001", selected_option="A"),
        AnswerRecord(question_id="LC-002", selected_option="A"),
        AnswerRecord(question_id="LC-003", selected_option="C"),
    ]
    results = evaluate_session(QUESTIONS, answers)
    summary = build_summary(SECTION, QUESTIONS, results)

    assert summary.section is SECTION
    assert summary.total_questions == 3
    assert summary.correct_count == 2
    assert summary.incorrect_count == 1
    assert summary.score == pytest.approx(2 / 3)

    por_tema = {tp.topic: tp for tp in summary.by_topic}
    assert por_tema["Comprensión de textos"].total == 2
    assert por_tema["Comprensión de textos"].correct == 2
    assert por_tema["Inferencia"].total == 1
    assert por_tema["Inferencia"].correct == 0


def test_build_summary_con_todas_correctas():
    answers = [
        AnswerRecord(question_id="LC-001", selected_option="A"),
        AnswerRecord(question_id="LC-002", selected_option="B"),
    ]
    results = evaluate_session(QUESTIONS, answers)
    summary = build_summary(SECTION, QUESTIONS, results)
    assert summary.score == 1.0
    assert summary.incorrect_count == 0


def test_build_summary_sin_respuestas():
    summary = build_summary(SECTION, QUESTIONS, [])
    assert summary.total_questions == 0
    assert summary.score == 0.0
    assert summary.by_topic == []