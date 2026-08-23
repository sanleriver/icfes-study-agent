import uuid

import streamlit as st
from langgraph.types import Command

from src.data.images import image_source
from src.graph import build_graph
from src.models import Question, Section
from src.providers import MockFeedbackProvider, create_feedback_provider


def init_state() -> None:
    """Inicializa el estado persistente de la sesión de Streamlit.

    El grafo compilado (con su checkpointer `InMemorySaver`) se guarda una sola
    vez en `st.session_state`; los reruns de Streamlit conservan el `thread_id`
    y la pregunta pendiente entre eventos.
    """
    if "graph" not in st.session_state:
        try:
            provider = create_feedback_provider()
        except ValueError as exc:
            st.error(str(exc))
            provider = MockFeedbackProvider()
        st.session_state["graph"] = build_graph(feedback_provider=provider)
        st.session_state["provider"] = provider.__class__.__name__
    if "thread_id" not in st.session_state:
        st.session_state["thread_id"] = uuid.uuid4().hex
    if "pending" not in st.session_state:
        st.session_state["pending"] = None
    if "final" not in st.session_state:
        st.session_state["final"] = None
    if "answered" not in st.session_state:
        st.session_state["answered"] = 0
    if "message" not in st.session_state:
        st.session_state["message"] = ""


def reset_session() -> None:
    """Reinicia la sesión con un nuevo `thread_id` (descarta el estado del grafo)."""
    st.session_state["thread_id"] = uuid.uuid4().hex
    st.session_state["pending"] = None
    st.session_state["final"] = None
    st.session_state["answered"] = 0
    st.session_state["message"] = ""
    st.rerun()


def _config() -> dict:
    return {"configurable": {"thread_id": st.session_state["thread_id"]}}


def start_session(section: Section, num_questions: int) -> None:
    """Invoca el grafo para iniciar la sesión y guarda la primera pregunta."""
    result = st.session_state["graph"].invoke(
        {"section": section, "num_questions": num_questions}, _config()
    )
    if result.get("message"):
        st.session_state["message"] = result["message"]
    interrupt = result.get("__interrupt__")
    if interrupt:
        st.session_state["pending"] = interrupt[0].value
    else:
        st.session_state["final"] = result
    st.session_state["answered"] = 0
    st.rerun()


def submit_answer(selected_option: str) -> None:
    """Reanuda el grafo con la opción elegida y avanza a la siguiente pregunta."""
    result = st.session_state["graph"].invoke(Command(resume=selected_option), _config())
    st.session_state["answered"] += 1
    interrupt = result.get("__interrupt__")
    if interrupt:
        st.session_state["pending"] = interrupt[0].value
    else:
        st.session_state["pending"] = None
        st.session_state["final"] = result
    st.rerun()


def show_config() -> None:
    """Formulario de configuración: sección (5 opciones) y número de preguntas."""
    st.header("Configuración de la sesión")
    with st.form("config"):
        section = st.selectbox(
            "Sección",
            options=list(Section),
            format_func=lambda s: s.label,
        )
        num_questions = st.number_input(
            "Número de preguntas",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
        )
        submitted = st.form_submit_button("Iniciar sesión")
    if submitted:
        start_session(section, int(num_questions))


def show_question() -> None:
    """Presenta la pregunta actual (una a una) con su imagen si existe."""
    question = Question.model_validate(st.session_state["pending"])
    st.header(f"Pregunta {st.session_state['answered'] + 1}")
    if st.session_state["message"]:
        st.info(st.session_state["message"])
    st.write(question.statement)

    source = image_source(question)
    if source is not None:
        st.image(str(source), caption="Imagen de la pregunta")

    selected = st.radio(
        "Elige una opción",
        options=list(question.options.keys()),
        format_func=lambda k: f"{k}) {question.options[k]}",
    )
    if st.button("Responder", type="primary"):
        submit_answer(selected)


def show_results() -> None:
    """Muestra el resumen final, el desempeño por tema y el feedback de las incorrectas."""
    final = st.session_state["final"]
    summary = final["summary"]
    st.header("Resultados de la sesión")
    if st.session_state["message"]:
        st.info(st.session_state["message"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Puntaje", f"{summary.score:.0%}")
    col2.metric("Correctas", summary.correct_count)
    col3.metric("Incorrectas", summary.incorrect_count)

    st.subheader("Desempeño por tema")
    if summary.by_topic:
        for tp in summary.by_topic:
            st.write(f"- **{tp.topic}:** {tp.correct}/{tp.total} correctas")
    else:
        st.write("No hubo preguntas respondidas.")

    if final["feedbacks"]:
        st.subheader("Retroalimentación de respuestas incorrectas")
        for fb in final["feedbacks"]:
            with st.expander(f"Pregunta {fb.question_id}"):
                st.markdown(f"**Explicación conceptual:** {fb.explanation}")
                st.markdown(f"**Análisis del error:** {fb.error_analysis}")
                st.markdown(f"**Refuerzo positivo:** {fb.positive_reinforcement}")
                st.markdown(f"**Tema para repasar:** {fb.suggestion_topic}")

    if st.button("Nueva sesión"):
        reset_session()


def main() -> None:
    st.set_page_config(page_title="Tutor ICFES Saber Pro", page_icon="📚")
    init_state()

    st.title("Tutor adaptativo ICFES Saber Pro")

    with st.sidebar:
        st.write(f"Proveedor de feedback: `{st.session_state['provider']}`")
        if st.session_state["pending"] or st.session_state["final"]:
            if st.button("Abandonar y reiniciar"):
                reset_session()

    if st.session_state["pending"]:
        show_question()
    elif st.session_state["final"]:
        show_results()
    else:
        show_config()


if __name__ == "__main__":
    main()