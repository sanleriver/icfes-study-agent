from __future__ import annotations

import flet as ft

from flet_app.router import setup_router
from flet_app.theme import APP_THEME


def main(page: ft.Page) -> None:
    """Entry point de la app Flet — Tutor ICFES Saber Pro."""
    page.title = "Tutor ICFES Saber Pro"
    page.window.width = 900
    page.window.height = 700
    page.padding = 0
    page.theme = APP_THEME
    # Transición Cupertino entre vistas (Fase 6A) — si la API no existe en
    # esta versión de flet, se ignora silenciosamente (no rompe la app).
    try:
        trans = ft.PageTransitionTheme.CUPERTINO  # type: ignore[attr-defined]
        page.theme.page_transitions = ft.PageTransitionsTheme(
            windows=trans, macos=trans, linux=trans
        )
    except Exception:
        pass

    setup_router(page)


if __name__ == "__main__":
    import os
    import sys

    # En Docker (FLET_WEB=1 o --web en args) exponer en 0.0.0.0 para healthcheck.
    # `flet run --web` ya inyecta el modo web, pero `python flet_app/main.py` directo
    # necesita ft.app con host/port. Soportamos ambos sin romper local `ft.run(main)`.
    _is_web = os.getenv("FLET_WEB") == "1" or "--web" in sys.argv
    _port = int(os.getenv("FLET_PORT", os.getenv("PORT", "8000")))
    _host = os.getenv("FLET_HOST", "0.0.0.0")
    if _is_web and "--web" not in sys.argv:
        # Ejecución directa sin CLI `flet run` (ej: Docker CMD python flet_app/main.py)
        ft.app(target=main, view=ft.WEB_BROWSER, host=_host, port=_port)
    else:
        # `flet run --web` o local desktop (`ft.run` sin args abre ventana)
        ft.run(main)
