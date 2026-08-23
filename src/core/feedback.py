from src.models import EvaluationResult, Feedback, Question


def fallback_feedback(question: Question, result: EvaluationResult) -> Feedback:
    """Feedback determinista enriquecido a partir de la pregunta.

    Se usa como fallback cuando el proveedor LLM falla y como base del
    feedback generado en el grafo (Fase 4). No es genérico: incluye distractor
    y opción correcta con contexto de la pregunta.
    """
    # Explicación conceptual específica, no solo join de key_points
    if question.key_points:
        explanation = (
            f"En {question.topic}: {' '.join(question.key_points)}. "
            f"La pregunta plantea: \"{question.statement[:160]}{'...' if len(question.statement) > 160 else ''}\" "
            f"La opción correcta es {question.correct_option}) {question.options[question.correct_option]}."
        )
    else:
        explanation = (
            f"El tema central es {question.topic}. "
            f"La opción correcta es {question.correct_option}) {question.options[question.correct_option]}."
        )
    # Análisis del error específico del distractor elegido
    chosen_text = question.options.get(result.selected_option, result.selected_option)
    correct_text = question.options.get(result.correct_option, result.correct_option)
    error_analysis = (
        f"Elegiste {result.selected_option}) \"{chosen_text}\", pero la correcta es "
        f"{result.correct_option}) \"{correct_text}\". "
        "El distractor suele parecer plausible porque omite un matiz clave "
        f"de {question.topic.lower()}; revisa el enunciado y contrasta cada opción con los puntos clave."
    )
    return Feedback(
        question_id=question.id,
        explanation=explanation,
        error_analysis=error_analysis,
        positive_reinforcement="El error es parte del aprendizaje; con este repaso afianzarás el criterio para la próxima.",
        suggestion_topic=question.topic,
    )