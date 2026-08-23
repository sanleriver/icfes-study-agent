from src.models import EvaluationResult, Feedback, Question


def fallback_feedback(question: Question, result: EvaluationResult) -> Feedback:
    """Feedback determinista a partir de los puntos clave de la pregunta.

    Se usa como fallback cuando el proveedor LLM falla y como base del
    feedback generado en el grafo (Fase 4).
    """
    explanation = (
        " ".join(question.key_points)
        if question.key_points
        else f"El tema central es {question.topic}."
    )
    return Feedback(
        question_id=question.id,
        explanation=explanation,
        error_analysis=(
            f"Elegiste la opción {result.selected_option}, pero la respuesta "
            f"correcta es {result.correct_option}. Revisa el planteamiento "
            "antes de responder."
        ),
        positive_reinforcement="El error es parte del aprendizaje; sigue practicando.",
        suggestion_topic=question.topic,
    )