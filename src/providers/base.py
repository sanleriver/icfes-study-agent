from abc import ABC, abstractmethod

from src.models import EvaluationResult, Feedback, Question


class FeedbackProvider(ABC):
    """Interfaz abstracta del proveedor de retroalimentación.

    El grafo LangGraph la usa en el nodo `generate_feedback` para producir la
    retroalimentación pedagógica de cada respuesta incorrecta. Recibe la
    pregunta original y el resultado de la evaluación determinista.
    """

    @abstractmethod
    def generate_feedback(
        self,
        question: Question,
        result: EvaluationResult,
    ) -> Feedback:
        """Genera la retroalimentación pedagógica para una respuesta."""