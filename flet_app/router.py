from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flet_app.views import ConfigView, QuestionView, ResultsView

if TYPE_CHECKING:
    import flet as ft

logger = logging.getLogger(__name__)

ROUTES = {
    "/": ConfigView,
    "/question": QuestionView,
    "/results": ResultsView,
}


async def render_route(page: ft.Page, route: str) -> None:
    """Construye la vista correspondiente a la ruta y la renderiza.

    Función reutilizable: la usan `on_route_change`, el render inicial y las
    vistas que necesitan re-montarse sobre su propia ruta (p. ej. QuestionView
    tras responder), ya que push_route() a la misma ruta NO dispara el evento
    (`Page.before_event` suprime rutas repetidas — verificado en fuente 0.86.5).
    """
    try:
        page.views.clear()

        view_cls = ROUTES.get(route)
        if view_cls is not None:
            view = view_cls(page)
            page.views.append(await view.build())

        page.update()
    except Exception:
        logger.exception("Error construyendo la vista para la ruta %s", route)
        raise


def setup_router(page: ft.Page) -> None:
    """Configura el router en la página Flet."""

    async def on_route_change(e: ft.RouteChangeEvent) -> None:
        await render_route(page, e.route)

    page.on_route_change = on_route_change
    # Render inicial: al arrancar la ruta del cliente ya es "/" y push_route("/")
    # no dispara on_route_change (la ruta no cambia), por eso se renderiza directo.
    page.run_task(render_route, page, page.route)
