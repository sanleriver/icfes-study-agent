from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import flet as ft

from flet_app.state.session_manager import SessionManager
from flet_app.theme import ACCENT as _ACCENT
from flet_app.theme import ACCENT_TINT as _ACCENT_TINT
from flet_app.theme import BG as _BG
from flet_app.theme import BORDER as _BORDER
from flet_app.theme import PAGE_MAX_WIDTH as _PAGE_MAX_WIDTH
from flet_app.theme import PAGE_PADDING as _PAGE_PADDING
from flet_app.theme import SURFACE as _SURFACE
from flet_app.theme import TEXT_MUTED as _TEXT_MUTED
from flet_app.theme import TEXT_PRIMARY as _TEXT_PRIMARY
from src.data.images import image_source
from src.models import Question

logger = logging.getLogger(__name__)

_ASSETS_IMAGES_DIR = Path(__file__).resolve().parents[1] / "assets" / "images"
_OPTION_KEYS = ("A", "B", "C", "D")


class QuestionView:
    """Pantalla de pregunta — presenta las preguntas una a una (US-03).

    El grafo pausa con `interrupt()` en cada pregunta; esta vista re-monta su
    propia ruta vía `render_route` tras responder para ejecutar el `resume()`
    correspondiente, porque `push_route()` a la misma ruta NO dispara
    `on_route_change` (`Page.before_event` suprime rutas repetidas).
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.manager = SessionManager(page)
        self._selected: str | None = None
        self._option_tiles: dict[str, ft.Container] = {}
        self.submit_button: ft.FilledButton | None = None
        self._card: ft.Container | None = None
        self._card_overlay: ft.Container | None = None

    def _effective_width(self) -> int:
        """Ancho efectivo responsive: min(1140, viewport-64) para centrado universal."""
        try:
            vw = self.page.width
            if vw is None or vw <= 0:
                vw = self.page.window.width
            if vw is None or vw <= 0:
                return _PAGE_MAX_WIDTH
            return max(311, min(_PAGE_MAX_WIDTH, int(vw - 2 * _PAGE_PADDING)))
        except Exception:
            return _PAGE_MAX_WIDTH

    # ------------------------------------------------------------------
    # Ciclo de vida de la vista (invoke / resume)
    # ------------------------------------------------------------------

    async def build(self) -> ft.View:
        try:
            return await self._build_session()
        except Exception:
            logger.exception("Error preparando la pregunta")
            self._show_snack(
                "Ocurrió un error al preparar la pregunta. Revisa la consola.",
                error=True,
            )
            return ft.View(controls=[], route="/question")

    async def _build_session(self) -> ft.View:
        runner = self.manager.get_graph_runner()
        if runner is None:
            # Deep-link a /question sin sesión configurada.
            self._show_snack("Inicia una sesión desde la pantalla de configuración.")
            self._deferred_navigate("/")
            return ft.View(controls=[], route="/question")

        pending = self.manager.get_pending_answer()
        if pending is not None:
            result = await runner.resume(pending)
            self.manager.clear_pending_answer()
        elif self.manager.get_final_result() is not None:
            # La sesión ya terminó: nada que preguntar.
            self._deferred_navigate("/results")
            return ft.View(controls=[], route="/question")
        else:
            result = await runner.invoke(
                {
                    "section": self.manager.get_section(),
                    "num_questions": self.manager.get_num_questions(),
                }
            )
            if result.get("message"):
                self._show_snack(result["message"])

        interrupt = result.get("__interrupt__")
        if interrupt:
            q_data = interrupt[0].value
            self.manager.set_current_question(q_data)
            answered = len(result.get("answers") or [])
            total = len(result.get("questions") or [])
            # Fase 6A — guardar progreso para detectar última pregunta en _on_submit
            self.manager.set_total_questions(total)
            self.manager.set_current_index(answered + 1)
            return self._render_question(q_data, answered + 1, total)

        self.manager.set_final_result(result)
        self._deferred_navigate("/results")
        return ft.View(controls=[], route="/question")

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _render_question(
        self, q_data: dict[str, Any], index: int, total: int
    ) -> ft.View:
        q = Question.model_validate(q_data)

        header = ft.Column(
            [
                ft.Text(
                    f"PREGUNTA {index} DE {total}",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=_TEXT_MUTED,
                ),
                ft.Text(q.topic, size=12.5, color=_TEXT_MUTED),
            ],
            spacing=2,
        )

        self._selected = None
        self._option_tiles = {}
        options_column = ft.Column(
            [self._option_tile(k, q.options[k]) for k in _OPTION_KEYS],
            spacing=10,
        )

        ew = self._effective_width()
        self.submit_button = ft.FilledButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK, size=20),
                    ft.Text("Responder", weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            ),
            width=ew - 48,
            height=48,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            disabled=True,
            on_click=self._on_submit,
        )

        card_children: list[ft.Control] = [header, ft.Text(q.statement, size=16, color=_TEXT_PRIMARY)]
        image_control = self._build_image(q)
        if image_control is not None:
            card_children.append(image_control)
        card_children += [options_column, self.submit_button]

        self._card = ft.Container(
            content=ft.Column(card_children, spacing=14),
            width=ew,
            bgcolor=_SURFACE,
            border=ft.Border.all(1.5, _BORDER),
            border_radius=12,
            padding=24,
        )

        # Velo solo sobre la tarjeta para "Calculando resultados…" (Fase 6A refinado)
        self._card_overlay = ft.Container(
            visible=False,
            width=ew,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.68, ft.Colors.WHITE),
            alignment=ft.Alignment.CENTER,
            padding=16,
            content=ft.Container(
                bgcolor=_SURFACE,
                border=ft.Border.all(1.5, _BORDER),
                border_radius=12,
                padding=24,
                width=340,
                shadow=ft.BoxShadow(
                    blur_radius=16,
                    color=ft.Colors.with_opacity(0.12, ft.Colors.GREY_900),
                ),
                content=ft.Column(
                    [
                        ft.ProgressRing(width=36, height=36, stroke_width=3.5, color=_ACCENT),
                        ft.Text(
                            "Calculando resultados…",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=_TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Evaluando respuestas y generando retroalimentación",
                            size=12.5,
                            color=_TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    tight=True,
                ),
            ),
        )

        card_stack = ft.Stack(controls=[self._card, self._card_overlay], width=ew)

        # Shell fullscreen: centrado universal H, arriba, scroll + ResponsiveRow (Plan A)
        shell_column = ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            col={"xs": 12},
                            content=ft.Container(
                                content=card_stack,
                                alignment=ft.Alignment.TOP_CENTER,
                            ),
                            alignment=ft.Alignment.TOP_CENTER,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.View(
            controls=[
                ft.Container(
                    content=shell_column,
                    padding=_PAGE_PADDING,
                    bgcolor=_BG,
                    expand=True,
                )
            ],
            route="/question",
            bgcolor=_BG,
        )

    def _build_image(self, q: Question) -> ft.Control | None:
        """Imagen del enunciado desde assets locales o URL (US-08 / imágenes)."""
        source = image_source(q)
        if source is None:
            return None
        if isinstance(source, Path):
            # Relativo a flet_app/assets (funciona desktop + web assets_dir)
            src = f"images/{source.name}"
        else:
            src = source
        ew = self._effective_width()
        img_w = max(200, ew - 48)
        # Compat 0.86.5: ImageFit no existe como top-level, usar BoxFit
        fit = getattr(ft, "ImageFit", getattr(ft, "BoxFit", None))
        fit_val = fit.CONTAIN if fit is not None else "contain"
        return ft.Container(
            content=ft.Image(
                src=src,
                height=280,
                width=img_w,
                fit=fit_val,
                border_radius=12,
            ),
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            alignment=ft.Alignment.CENTER,
        )

    def _option_tile(self, key: str, text: str) -> ft.Container:
        row = ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        key, size=14, weight=ft.FontWeight.BOLD, color=_ACCENT
                    ),
                    width=28,
                ),
                ft.Text(text, size=13.5, color=_TEXT_PRIMARY, expand=True),
            ],
            spacing=10,
        )
        tile = ft.Container(
            content=row,
            ink=True,
            border_radius=12,
            padding=ft.Padding(14, 12, 14, 12),
            border=ft.Border.all(1.5, _BORDER),
            on_click=lambda _, k=key: self._select_option(k),
        )
        self._option_tiles[key] = tile
        return tile

    # ------------------------------------------------------------------
    # Manejadores internos
    # ------------------------------------------------------------------

    def _select_option(self, key: str) -> None:
        self._selected = key
        for k, tile in self._option_tiles.items():
            selected = k == key
            tile.bgcolor = _ACCENT_TINT if selected else None
            tile.border = ft.Border.all(2 if selected else 1.5, _ACCENT if selected else _BORDER)
        assert self.submit_button is not None
        self.submit_button.disabled = False
        self.page.update()

    async def _on_submit(self, event: ft.ControlEvent) -> None:
        if self._selected is None:
            return
        button = self.submit_button
        assert button is not None

        # Fase 6A — detectar última pregunta para mostrar overlay más visible
        total = self.manager.get_total_questions()
        idx = self.manager.get_current_index()
        is_last = isinstance(total, int) and isinstance(idx, int) and idx >= total

        button.disabled = True
        if is_last:
            button.content = ft.Row(
                [
                    ft.ProgressRing(width=28, height=28, stroke_width=3),
                    ft.Text(
                        "Calculando resultados…",
                        weight=ft.FontWeight.W_600,
                        size=14,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            )
        else:
            button.content = ft.Row(
                [
                    ft.ProgressRing(width=20, height=20, stroke_width=2.5),
                    ft.Text("Enviando respuesta…", weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            )
        # Overlay deshabilitado: atenuar y bloquear tiles clicables
        for tile in self._option_tiles.values():
            tile.disabled = True
            tile.opacity = 0.6
        if is_last and self._card is not None and self._card_overlay is not None:
            self._card.opacity = 0.55
            self._card_overlay.visible = True
        self.page.update()

        try:
            # Import perezoso: evita la dependencia circular router ↔ views.
            from flet_app.router import render_route

            self.manager.set_pending_answer(self._selected)
            await render_route(self.page, "/question")
        except Exception:
            logger.exception("Error al enviar la respuesta")
            self._show_snack(
                "No se pudo registrar la respuesta. Inténtalo de nuevo.",
                error=True,
            )
            button.disabled = False
            button.content = ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK, size=20),
                    ft.Text("Responder", weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            )
            if self._card is not None:
                self._card.opacity = 1.0
            if self._card_overlay is not None:
                self._card_overlay.visible = False
            for tile in self._option_tiles.values():
                tile.disabled = False
                tile.opacity = 1.0
            self.page.update()

    def _deferred_navigate(self, route: str) -> None:
        """Navega cuando termine el render actual.

        Evita que el route change anidado se solape con el `render_route`
        en curso (el cual aún debe añadir la vista devuelta por `build`).
        """
        async def go() -> None:
            await self.page.push_route(route)

        self.page.run_task(go)

    def _show_snack(self, message: str, error: bool = False) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_600 if error else _ACCENT,
                duration=4000,
            )
        )
