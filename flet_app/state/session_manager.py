from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.models import Section

from .graph_runner import GraphRunner

if TYPE_CHECKING:
    import flet as ft


class SessionManager:
    """Wrapper sobre `page.session.store` de Flet.

    Proporciona una API limpia para manejar el estado de la sesión del tutor:
    - `graph_runner`: instancia singleton de `GraphRunner`
    - `section`: sección del examen elegida
    - `num_questions`: cantidad de preguntas de la sesión
    - `current_question`: datos de la pregunta actual (dict del interrupt)
    - `pending_answer`: opción seleccionada pendiente de enviar al grafo
    - `final_result`: resultado final de la sesión (dict completo del grafo)

    El `thread_id` persistente lo gestiona `GraphRunner` via `SharedPreferences`.
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # GraphRunner (singleton por sesión)
    # ------------------------------------------------------------------

    def get_graph_runner(self) -> GraphRunner | None:
        """Obtiene el GraphRunner de la sesión. None si no se ha inicializado."""
        return self.page.session.store.get("graph_runner")

    def set_graph_runner(self, runner: GraphRunner) -> None:
        """Guarda el GraphRunner en la sesión."""
        self.page.session.store.set("graph_runner", runner)

    # ------------------------------------------------------------------
    # Sección y configuración
    # ------------------------------------------------------------------

    def get_section(self) -> Section | None:
        raw = self.page.session.store.get("section")
        if raw is None:
            return None
        return Section(raw) if isinstance(raw, str) else raw

    def set_section(self, section: Section) -> None:
        self.page.session.store.set("section", section.value)

    def get_num_questions(self) -> int:
        return self.page.session.store.get("num_questions") or 10

    def set_num_questions(self, n: int) -> None:
        self.page.session.store.set("num_questions", n)

    # ------------------------------------------------------------------
    # Estado de la pregunta
    # ------------------------------------------------------------------

    def get_current_question(self) -> dict[str, Any] | None:
        return self.page.session.store.get("current_question")

    def set_current_question(self, question_data: dict[str, Any]) -> None:
        self.page.session.store.set("current_question", question_data)

    # ------------------------------------------------------------------
    # Respuesta pendiente (para resume)
    # ------------------------------------------------------------------

    def get_pending_answer(self) -> str | None:
        val = self.page.session.store.get("pending_answer")
        return val if val is not None else None

    def set_pending_answer(self, option: str) -> None:
        self.page.session.store.set("pending_answer", option)

    def clear_pending_answer(self) -> None:
        self.page.session.store.set("pending_answer", None)

    # ------------------------------------------------------------------
    # Resultado final
    # ------------------------------------------------------------------

    def get_final_result(self) -> dict[str, Any] | None:
        return self.page.session.store.get("final_result")

    def set_final_result(self, result: dict[str, Any]) -> None:
        self.page.session.store.set("final_result", result)

    # ------------------------------------------------------------------
    # Progreso de la sesión (Fase 6A — para detectar última pregunta)
    # ------------------------------------------------------------------

    def get_total_questions(self) -> int | None:
        val = self.page.session.store.get("total_questions")
        return int(val) if isinstance(val, int) else None

    def set_total_questions(self, n: int) -> None:
        self.page.session.store.set("total_questions", int(n))

    def get_current_index(self) -> int | None:
        val = self.page.session.store.get("current_index")
        return int(val) if isinstance(val, int) else None

    def set_current_index(self, i: int) -> None:
        self.page.session.store.set("current_index", int(i))

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def reset_session_state(self) -> None:
        """Limpia las claves por-sesión (pregunta/pendiente/resultado) sin
        tocar la configuración ni el runner. Se invoca al iniciar una nueva
        sesión para que el guard de QuestionView no redirija a /results y
        las sesiones consecutivas sean ilimitadas."""
        self.page.session.store.set("current_question", None)
        self.page.session.store.set("pending_answer", None)
        self.page.session.store.set("final_result", None)
        self.page.session.store.set("total_questions", None)
        self.page.session.store.set("current_index", None)

    def clear_session(self) -> None:
        """Limpia todo el estado de sesión de la vista (no borra thread_id)."""
        self.page.session.store.set("graph_runner", None)
        self.page.session.store.set("section", None)
        self.page.session.store.set("num_questions", 10)
        self.page.session.store.set("current_question", None)
        self.page.session.store.set("pending_answer", None)
        self.page.session.store.set("final_result", None)
        self.page.session.store.set("total_questions", None)
        self.page.session.store.set("current_index", None)
