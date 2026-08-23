import operator
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from .question import OPTION_KEYS, Question
from .section import Section


class AnswerRecord(BaseModel):
    """Respuesta del estudiante a una pregunta."""

    question_id: str
    selected_option: str

    @field_validator("selected_option")
    @classmethod
    def validate_selected_option(cls, value: str) -> str:
        if value not in OPTION_KEYS:
            raise ValueError(f"La opción seleccionada debe ser una de {OPTION_KEYS}")
        return value


class EvaluationResult(BaseModel):
    """Resultado determinista de la evaluación de una respuesta."""

    question_id: str
    selected_option: str
    correct_option: str
    is_correct: bool


class Feedback(BaseModel):
    """Retroalimentación pedagógica generada por el proveedor LLM."""

    question_id: str
    explanation: str
    error_analysis: str = ""
    positive_reinforcement: str = ""
    suggestion_topic: str = ""


class TopicPerformance(BaseModel):
    """Desempeño agregado por tema dentro de la sección estudiada."""

    topic: str
    total: int
    correct: int


class Summary(BaseModel):
    """Resumen final de la sesión de estudio."""

    section: Section
    total_questions: int
    correct_count: int
    incorrect_count: int
    score: float = Field(ge=0.0, le=1.0)
    by_topic: list[TopicPerformance] = Field(default_factory=list)


class SessionState(BaseModel):
    """Estado tipado de la sesión de estudio (esquema del grafo LangGraph).

    - Los campos con reducer `operator.add` acumulan valores sin sobrescribir.
    - Los campos sin reducer se sobrescriben en cada actualización.
    """

    section: Section | None = None
    num_questions: int = Field(default=10, ge=1)
    questions: list[Question] = Field(default_factory=list)
    answers: Annotated[list[AnswerRecord], operator.add] = Field(default_factory=list)
    results: list[EvaluationResult] = Field(default_factory=list)
    feedbacks: list[Feedback] = Field(default_factory=list)
    summary: Summary | None = None
    message: str = ""