from __future__ import annotations

import logging
from typing import Any

import flet as ft

from flet_app.components import MetricCard, build_feedback_panels
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
from src.models import Feedback, Summary, TopicPerformance

logger = logging.getLogger(__name__)


class ResultsView:
    """Pantalla de resultados — métricas + desempeño por tema + feedback (US-05/US-06/US-08).

    Diseño «Académico sereno»: fondo GREY_50, tarjetas blancas radio 12,
    jerarquía 28 BOLD / 11 BOLD uppercase / 13-14 body, un único acento
    INDIGO_600 (verde/rojo solo como semántica correcto/incorrecto).
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.manager = SessionManager(page)

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
    # Ciclo de vida
    # ------------------------------------------------------------------

    async def build(self) -> ft.View:
        try:
            return await self._build_results()
        except Exception:
            logger.exception("Error preparando la vista de resultados")
            self._show_snack(
                "Ocurrió un error al mostrar los resultados. Revisa la consola.",
                error=True,
            )
            return ft.View(controls=[], route="/results")

    async def _build_results(self) -> ft.View:
        final = self.manager.get_final_result()
        if final is None:
            self._show_snack("Inicia una sesión desde la pantalla de configuración.")
            self._deferred_navigate("/")
            return ft.View(controls=[], route="/results")

        summary = self._parse_summary(final.get("summary"))
        feedbacks = self._parse_feedbacks(final.get("feedbacks"))

        # Métricas — fila de 3 (equiv. st.columns(3) + st.metric)
        score_text = f"{summary.score:.0%}" if summary is not None else "—"
        correct_text = str(summary.correct_count) if summary is not None else "—"
        incorrect_text = str(summary.incorrect_count) if summary is not None else "—"

        metrics_row = ft.Row(
            [
                MetricCard("Puntaje", score_text, _ACCENT),
                MetricCard("Correctas", correct_text, ft.Colors.GREEN_600),
                MetricCard("Incorrectas", incorrect_text, ft.Colors.RED_600),
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Desempeño por tema
        by_topic_block = self._build_by_topic_block(summary)

        # Feedback expandible
        feedback_block = self._build_feedback_block(feedbacks)

        # Banner de aviso del banco (agotamiento) si existe
        message = final.get("message") if isinstance(final, dict) else None
        banner: ft.Control | None = None
        if isinstance(message, str) and message.strip():
            banner = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=_ACCENT),
                        ft.Text(message, size=12.5, color=_TEXT_PRIMARY, expand=True),
                    ],
                    spacing=8,
                ),
                bgcolor=_ACCENT_TINT,
                border=ft.Border.all(1, ft.Colors.INDIGO_200),
                border_radius=8,
                padding=ft.Padding(12, 10, 12, 10),
            )

        new_session_button = ft.FilledButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.REFRESH, size=20),
                    ft.Text("Nueva sesión", weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            ),
            height=48,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            on_click=self._on_new_session,
        )

        # Botón full-width: envolver en Row expand para ocupar el ancho.
        button_row = ft.Row([new_session_button], expand=False)
        # Flet: el botón debe expandirse; usar expand en el propio botón si
        # está dentro de Row funciona; alternativamente asignar expand.
        new_session_button.expand = True

        header = ft.Row(
            [
                ft.Container(
                    content=ft.Image(
                        src="icons/logo.png",
                        width=56,
                        height=56,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    width=56,
                    height=56,
                    border_radius=ft.BorderRadius.all(14),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                ft.Column(
                    [
                        ft.Text(
                            "Resultados de la sesión",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=_TEXT_PRIMARY,
                        ),
                        ft.Text(
                            summary.section.label if summary and summary.section else "Resumen de desempeño",
                            size=13.5,
                            color=_TEXT_MUTED,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            spacing=16,
        )

        content_children: list[ft.Control] = [
            header,
            ft.Container(height=10),
        ]
        if banner is not None:
            content_children.append(banner)
            content_children.append(ft.Container(height=6))
        content_children += [
            metrics_row,
            ft.Container(height=6),
            by_topic_block,
            ft.Container(height=6),
            feedback_block,
            ft.Container(height=12),
            button_row,
        ]

        ew = self._effective_width()
        content_column = ft.Column(
            content_children,
            spacing=10,
        )

        inner = ft.Container(
            content=content_column,
            width=ew,
            alignment=ft.Alignment.TOP_CENTER,
        )

        shell_column = ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            col={"xs": 12},
                            content=inner,
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
            route="/results",
            bgcolor=_BG,
        )

    # ------------------------------------------------------------------
    # Sub-bloques
    # ------------------------------------------------------------------

    def _parse_summary(self, raw: Any) -> Summary | None:
        if raw is None:
            return None
        if isinstance(raw, Summary):
            return raw
        if isinstance(raw, dict):
            try:
                return Summary.model_validate(raw)
            except Exception:
                logger.exception("No se pudo validar el summary del resultado final")
                return None
        return None

    def _parse_feedbacks(self, raw: Any) -> list[Feedback]:
        if not raw:
            return []
        parsed: list[Feedback] = []
        for item in raw:
            if isinstance(item, Feedback):
                parsed.append(item)
            elif isinstance(item, dict):
                try:
                    parsed.append(Feedback.model_validate(item))
                except Exception:
                    logger.exception("Feedback inválido ignorado: %r", item)
            else:
                # Objeto con atributos compatibles
                try:
                    parsed.append(Feedback.model_validate(item))
                except Exception:
                    logger.exception("Feedback no parseable ignorado: %r", item)
        return parsed

    def _build_by_topic_block(self, summary: Summary | None) -> ft.Control:
        title = ft.Text(
            "DESEMPEÑO POR TEMA",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=_TEXT_MUTED,
        )
        if summary is None or not summary.by_topic:
            body = ft.Text(
                "No hubo preguntas respondidas.",
                size=13.5,
                color=_TEXT_MUTED,
            )
        else:
            rows: list[ft.Control] = []
            for tp in summary.by_topic:
                # tp puede venir como dict si el summary fue reconstruido parcialmente
                if isinstance(tp, dict):
                    try:
                        tp = TopicPerformance.model_validate(tp)
                    except Exception:
                        continue
                # Barra sutil de progreso por tema (fondo gris + relleno índigo)
                pct = (tp.correct / tp.total) if tp.total else 0
                rows.append(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(tp.topic, size=13.5, color=_TEXT_PRIMARY, expand=True),
                                    ft.Text(
                                        f"{tp.correct}/{tp.total}",
                                        size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=_TEXT_PRIMARY,
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.ProgressBar(
                                value=pct,
                                color=_ACCENT,
                                bgcolor=ft.Colors.GREY_200,
                                height=6,
                                border_radius=3,
                            ),
                        ],
                        spacing=6,
                    )
                )
            body = ft.Column(rows, spacing=12)

        card = ft.Container(
            content=ft.Column([title, body], spacing=10),
            bgcolor=_SURFACE,
            border=ft.Border.all(1.5, _BORDER),
            border_radius=12,
            padding=16,
        )
        return card

    def _build_feedback_block(self, feedbacks: list[Feedback]) -> ft.Control:
        title = ft.Text(
            "RETROALIMENTACIÓN",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=_TEXT_MUTED,
        )
        if not feedbacks:
            body: ft.Control = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=ft.Colors.GREEN_600),
                        ft.Text(
                            "¡Excelente! No hay respuestas incorrectas para repasar.",
                            size=13.5,
                            color=_TEXT_MUTED,
                        ),
                    ],
                    spacing=8,
                ),
                bgcolor=_SURFACE,
                border=ft.Border.all(1.5, _BORDER),
                border_radius=12,
                padding=16,
            )
            return ft.Column([title, body], spacing=8)

        panel_list = build_feedback_panels(feedbacks)
        assert panel_list is not None
        # Contenedor para dar borde/padding coherente al ExpansionPanelList
        list_container = ft.Container(
            content=panel_list,
            bgcolor=_SURFACE,
            border=ft.Border.all(1.5, _BORDER),
            border_radius=12,
            padding=8,
        )
        hint = ft.Text(
            "Expande cada tarjeta para ver la explicación conceptual, el análisis del error, el refuerzo y el tema a repasar.",
            size=12.5,
            color=_TEXT_MUTED,
        )
        return ft.Column([title, hint, list_container], spacing=8)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _on_new_session(self, _) -> None:
        """Reinicia la sesión (US-07) — mismo reset que ConfigView._on_start."""
        try:
            runner = self.manager.get_graph_runner()
            self.manager.reset_session_state()
            if runner is not None:
                await runner.new_thread()
            await self.page.push_route("/")
        except Exception:
            logger.exception("Error al reiniciar la sesión")
            self._show_snack(
                "No se pudo reiniciar la sesión. Revisa la consola.",
                error=True,
            )

    def _deferred_navigate(self, route: str) -> None:
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
