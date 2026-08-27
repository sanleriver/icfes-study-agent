from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from flet.controls.services.shared_preferences import SharedPreferences

from src.models import Section

from .graph_runner import GraphRunner

if TYPE_CHECKING:
    import flet as ft


class SessionManager:
    """Wrapper sobre `page.session.store` de Flet con persistencia durable.

    Fase B: `page.session.store` es volátil (se pierde en F5 / cambio de
    pestaña). Para que el progreso sobreviva, cada setter escribe además
    en `SharedPreferences` (JSON) y cada getter hace fallback a prefs si el
    store está vacío. El `thread_id` lo gestiona `GraphRunner` vía prefs
    y el checkpointer SQLite es la fuente de verdad (`GraphRunner.get_state`).

    Claves persistentes: section, num_questions, current_question,
    pending_answer, final_result, total_questions, current_index.
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._prefs = SharedPreferences()

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
    # Persistencia durable (SharedPreferences JSON) — Fase B
    # ------------------------------------------------------------------

    async def _persist(self, key: str, value: Any) -> None:
        """Guarda en SharedPreferences (JSON si es dict/list)."""
        try:
            if value is None:
                await self._prefs.set(key, "")
            elif isinstance(value, (dict, list)):
                await self._prefs.set(key, json.dumps(value, ensure_ascii=False))
            elif isinstance(value, (str, int, float, bool)):
                await self._prefs.set(key, value)
            else:
                await self._prefs.set(key, json.dumps(value, ensure_ascii=False, default=str))
        except Exception:
            pass  # no bloquear UI por fallo de prefs

    async def _load(self, key: str) -> Any:
        try:
            raw = await self._prefs.get(key)
            if raw is None or raw == "":
                return None
            if isinstance(raw, (dict, list, int, float, bool)):
                return raw
            # intentar JSON
            try:
                return json.loads(raw)
            except Exception:
                return raw
        except Exception:
            return None

    async def persist_section(self, section: Section) -> None:
        self.set_section(section)
        await self._persist("section", section.value)

    async def persist_num_questions(self, n: int) -> None:
        self.set_num_questions(n)
        await self._persist("num_questions", int(n))

    async def persist_current_question(self, q_data: dict[str, Any]) -> None:
        self.set_current_question(q_data)
        await self._persist("current_question", q_data)

    async def persist_pending_answer(self, option: str) -> None:
        self.set_pending_answer(option)
        await self._persist("pending_answer", option)

    async def persist_final_result(self, result: dict[str, Any]) -> None:
        self.set_final_result(result)
        # serializar summary/feedbacks puede contener Pydantic; json default=str
        await self._persist("final_result", result)

    async def persist_progress(self, total: int, index: int) -> None:
        self.set_total_questions(total)
        self.set_current_index(index)
        await self._persist("total_questions", int(total))
        await self._persist("current_index", int(index))

    async def hydrate_session(self) -> None:
        """Hidrata `page.session.store` desde SharedPreferences si está vacío."""
        try:
            if self.page.session.store.get("section") is None:
                raw = await self._load("section")
                if isinstance(raw, str) and raw:
                    try:
                        self.page.session.store.set("section", raw)
                    except Exception:
                        pass
            if self.page.session.store.get("num_questions") is None:
                raw = await self._load("num_questions")
                if isinstance(raw, int):
                    self.page.session.store.set("num_questions", raw)
            if self.page.session.store.get("current_question") is None:
                raw = await self._load("current_question")
                if isinstance(raw, dict):
                    self.page.session.store.set("current_question", raw)
            if self.page.session.store.get("pending_answer") is None:
                raw = await self._load("pending_answer")
                if isinstance(raw, str) and raw:
                    self.page.session.store.set("pending_answer", raw)
            if self.page.session.store.get("final_result") is None:
                raw = await self._load("final_result")
                if isinstance(raw, dict):
                    self.page.session.store.set("final_result", raw)
            if self.page.session.store.get("total_questions") is None:
                raw = await self._load("total_questions")
                if isinstance(raw, int):
                    self.page.session.store.set("total_questions", raw)
            if self.page.session.store.get("current_index") is None:
                raw = await self._load("current_index")
                if isinstance(raw, int):
                    self.page.session.store.set("current_index", raw)
        except Exception:
            pass

    async def clear_persistent_state(self) -> None:
        """Limpia tanto session.store como SharedPreferences por-sesión."""
        self.reset_session_state()
        for k in ("current_question", "pending_answer", "final_result", "total_questions", "current_index"):
            try:
                await self._prefs.set(k, "")
            except Exception:
                pass

    async def clear_all_persistent(self) -> None:
        self.clear_session()
        for k in ("section", "num_questions", "current_question", "pending_answer", "final_result", "total_questions", "current_index"):
            try:
                await self._prefs.set(k, "")
            except Exception:
                pass

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
