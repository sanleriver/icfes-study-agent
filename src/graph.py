import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.core.evaluation import build_summary, evaluate_session
from src.data.loader import random_sample
from src.models import AnswerRecord, SessionState
from src.providers import FeedbackProvider, MockFeedbackProvider

# ------------------------------------------------------------------
# Checkpointer persistente (Fase B)
# ------------------------------------------------------------------
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "checkpoints.db"


def _build_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("src.models.section", "Section"),
            ("src.models.question", "Question"),
            ("src.models.session", "AnswerRecord"),
            ("src.models.session", "EvaluationResult"),
            ("src.models.session", "Feedback"),
        ]
    )


def create_sqlite_saver(db_path: str | Path | None = None):
    """Crea un `SqliteSaver` persistente.

    Si `langgraph-checkpoint-sqlite` no está instalado, hace fallback a
    `InMemorySaver` (útil para tests sin el extra).
    """
    serde = _build_serde()
    path = Path(db_path) if db_path is not None else _DEFAULT_DB_PATH
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        # Asegurar directorio padre
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        saver = SqliteSaver(conn, serde=serde)
        # setup lazy via cursor; forzar creación de tablas ya
        saver.setup()
        return saver
    except ImportError:
        return InMemorySaver(serde=serde)


def get_default_db_path() -> Path:
    return _DEFAULT_DB_PATH


def initialize_session(state: SessionState) -> dict:
    """Selecciona las preguntas aleatorias de la sección y notifica si el
    banco no alcanza a cubrir `num_questions`."""
    if state.section is None:
        raise ValueError("Se requiere una sección para inicializar la sesión")

    questions = random_sample(state.section, state.num_questions)
    message = ""
    if len(questions) < state.num_questions:
        message = (
            f"Solo hay {len(questions)} preguntas disponibles para la sección "
            f"{state.section.label}; se usarán todas."
        )
    return {"questions": questions, "message": message}


def next_question(state: SessionState) -> dict:
    """Presenta la siguiente pregunta pendiente y espera la respuesta del
    estudiante mediante `interrupt()`.

    Al reanudar, `interrupt()` devuelve la opción seleccionada, que se acumula
    en `answers` con el reducer. Se fusiona el registro de respuesta en este
    nodo porque al reanudar el nodo se re-ejecuta desde el inicio.
    """
    index = len(state.answers)
    if index >= len(state.questions):
        return {}

    question = state.questions[index]
    selected_option = interrupt(question.model_dump(mode="json"))
    record = AnswerRecord(question_id=question.id, selected_option=selected_option)
    return {"answers": [record]}


def evaluate_node(state: SessionState) -> dict:
    """Evalúa de forma determinista todas las respuestas de la sesión."""
    results = evaluate_session(state.questions, state.answers)
    return {"results": results}


def build_generate_feedback_node(provider: FeedbackProvider):
    """Crea el nodo `generate_feedback` inyectando el proveedor.

    Genera feedback únicamente para las respuestas incorrectas mediante el
    `FeedbackProvider` recibido (mock, Gemini o fallback determinista).
    Paraleliza con ThreadPoolExecutor para reducir latencia N incorrectas.
    """

    def generate_feedback(state: SessionState) -> dict:
        by_id = {q.id: q for q in state.questions}
        incorrect = [r for r in state.results if not r.is_correct]
        if not incorrect:
            return {"feedbacks": []}
        # Paralelo: 1 thread por incorrecta, max 4 para no saturar API
        if len(incorrect) == 1:
            feedbacks = [provider.generate_feedback(by_id[incorrect[0].question_id], incorrect[0])]
        else:
            from concurrent.futures import ThreadPoolExecutor

            def _gen(r):
                return provider.generate_feedback(by_id[r.question_id], r)

            max_workers = min(4, len(incorrect))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                feedbacks = list(executor.map(_gen, incorrect))
        return {"feedbacks": feedbacks}

    return generate_feedback


def generate_summary(state: SessionState) -> dict:
    """Construye el resumen final de la sesión."""
    summary = build_summary(state.section, state.questions, state.results)
    return {"summary": summary}


def should_continue(state: SessionState) -> str:
    """¿Quedan preguntas por responder? Si no, se evalúa la sesión."""
    if len(state.answers) < len(state.questions):
        return "next_question"
    return "evaluate_session"


def build_graph(
    feedback_provider: FeedbackProvider | None = None,
    checkpointer=None,
    db_path: str | Path | None = None,
):
    """Construye el grafo de la sesión de estudio.

    Compilado con checkpointer para soportar `interrupt()`.
    Cada pregunta requiere un `thread_id` y se reanuda con
    `Command(resume=opcion_seleccionada)`.

    `feedback_provider` inyecta el proveedor de retroalimentación del nodo
    `generate_feedback` (Fase 5). Si no se indica, se usa `MockFeedbackProvider`
    determinista para que la suite de tests no dependa de una API key.

    Persistencia (Fase B):
    - Si se pasa `checkpointer`, se usa tal cual.
    - Si se pasa `db_path`, crea un `SqliteSaver` persistente.
    - Si no se indica nada, usa `InMemorySaver` (compat tests).
      La app Flet debe pasar `db_path` o `create_sqlite_saver()` explícitamente
      para sobrevivir a F5/reinicio Docker.
    """
    provider = feedback_provider if feedback_provider is not None else MockFeedbackProvider()
    builder = StateGraph(SessionState)
    builder.add_node("initialize_session", initialize_session)
    builder.add_node("next_question", next_question)
    builder.add_node("evaluate_session", evaluate_node)
    builder.add_node("generate_feedback", build_generate_feedback_node(provider))
    builder.add_node("generate_summary", generate_summary)

    builder.add_edge(START, "initialize_session")
    builder.add_edge("initialize_session", "next_question")
    builder.add_conditional_edges(
        "next_question",
        should_continue,
        ["next_question", "evaluate_session"],
    )
    builder.add_edge("evaluate_session", "generate_feedback")
    builder.add_edge("generate_feedback", "generate_summary")
    builder.add_edge("generate_summary", END)

    if checkpointer is not None:
        saver = checkpointer
    elif db_path is not None:
        saver = create_sqlite_saver(db_path)
    else:
        saver = InMemorySaver(serde=_build_serde())
    return builder.compile(checkpointer=saver)