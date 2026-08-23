from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from langgraph.types import Command

from flet.controls.services.shared_preferences import SharedPreferences

from src.graph import build_graph
from src.providers import FeedbackProvider, MockFeedbackProvider

if TYPE_CHECKING:
    import flet as ft


class GraphRunner:
    """Async wrapper para el grafo LangGraph.

    Ejecuta `invoke` y `resume` en un thread separado via `asyncio.to_thread`
    para no bloquear el event loop de Flet. Gestiona `thread_id` y checkpoint
    para soportar human-in-the-loop (interrupt/resume).
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.graph: Any = None
        self.thread_id: str = ""
        self._prefs = SharedPreferences()

    async def initialize(self, provider: FeedbackProvider | None = None) -> None:
        """Inicializa el grafo y carga/crea el thread_id persistente."""
        prov = provider if provider is not None else MockFeedbackProvider()
        self.graph = build_graph(feedback_provider=prov)

        stored_id = await self._prefs.get("thread_id")
        if isinstance(stored_id, str) and stored_id:
            self.thread_id = stored_id
        else:
            self.thread_id = uuid.uuid4().hex
            await self._prefs.set("thread_id", self.thread_id)

    async def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta el grafo con los datos iniciales (start → interrupt)."""
        config = {"configurable": {"thread_id": self.thread_id}}
        result = await asyncio.to_thread(self.graph.invoke, input_data, config)
        return result

    async def resume(self, option: str) -> dict[str, Any]:
        """Reanuda el grafo con la opción seleccionada (Command resume)."""
        config = {"configurable": {"thread_id": self.thread_id}}
        result = await asyncio.to_thread(
            self.graph.invoke, Command(resume=option), config
        )
        return result

    async def new_thread(self) -> None:
        """Crea un nuevo thread_id para una sesión limpia."""
        self.thread_id = uuid.uuid4().hex
        await self._prefs.set("thread_id", self.thread_id)
