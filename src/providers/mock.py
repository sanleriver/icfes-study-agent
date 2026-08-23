from src.core.feedback import fallback_feedback
from src.models import EvaluationResult, Feedback, Question

from .base import FeedbackProvider


class MockFeedbackProvider(FeedbackProvider):
    """Proveedor determinista para desarrollo y tests sin API key.

    Delega en `fallback_feedback`, de modo que la salida es reproducible y no
    depende de ningún servicio externo. Ignora la imagen de la pregunta.
    """

    def generate_feedback(
        self,
        question: Question,
        result: EvaluationResult,
    ) -> Feedback:
        return fallback_feedback(question, result)