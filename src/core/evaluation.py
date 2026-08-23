from src.models import (
    AnswerRecord,
    EvaluationResult,
    Question,
    Section,
    Summary,
    TopicPerformance,
)


def evaluate_session(
    questions: list[Question],
    answers: list[AnswerRecord],
) -> list[EvaluationResult]:
    """Evalúa cada respuesta contra la opción correcta de su pregunta.

    Lanza `ValueError` si una respuesta referencia una pregunta inexistente.
    """
    by_id = {q.id: q for q in questions}
    results: list[EvaluationResult] = []
    for answer in answers:
        question = by_id.get(answer.question_id)
        if question is None:
            raise ValueError(
                f"La respuesta {answer.question_id} no corresponde a ninguna pregunta de la sesión"
            )
        results.append(
            EvaluationResult(
                question_id=answer.question_id,
                selected_option=answer.selected_option,
                correct_option=question.correct_option,
                is_correct=answer.selected_option == question.correct_option,
            )
        )
    return results


def incorrect_question_ids(results: list[EvaluationResult]) -> list[str]:
    """Devuelve los ids de las preguntas respondidas incorrectamente."""
    return [r.question_id for r in results if not r.is_correct]


def build_summary(
    section: Section,
    questions: list[Question],
    results: list[EvaluationResult],
) -> Summary:
    """Construye el resumen de la sesión: puntuación y desempeño por tema."""
    by_id = {q.id: q for q in questions}
    total = len(results)
    correct_count = sum(1 for r in results if r.is_correct)

    per_topic: dict[str, list[bool]] = {}
    for r in results:
        topic = by_id[r.question_id].topic
        per_topic.setdefault(topic, []).append(r.is_correct)
    by_topic = [
        TopicPerformance(topic=topic, total=len(flags), correct=sum(flags))
        for topic, flags in sorted(per_topic.items())
    ]

    score = correct_count / total if total else 0.0
    return Summary(
        section=section,
        total_questions=total,
        correct_count=correct_count,
        incorrect_count=total - correct_count,
        score=score,
        by_topic=by_topic,
    )