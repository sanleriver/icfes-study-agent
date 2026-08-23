from __future__ import annotations

import flet as ft

from flet_app.theme import ACCENT as _ACCENT
from flet_app.theme import BORDER as _BORDER
from flet_app.theme import SURFACE as _SURFACE
from flet_app.theme import TEXT_MUTED as _TEXT_MUTED
from flet_app.theme import TEXT_PRIMARY as _TEXT_PRIMARY
from src.models import Feedback


def _field_block(label: str, value: str) -> ft.Control:
    """Bloque label 11px uppercase + body 13-14px para un campo del feedback."""
    return ft.Column(
        [
            ft.Text(label.upper(), size=11, weight=ft.FontWeight.BOLD, color=_TEXT_MUTED),
            ft.Text(value, size=13.5, color=_TEXT_PRIMARY),
        ],
        spacing=4,
    )


class FeedbackExpander(ft.ExpansionPanel):
    """Panel expandible para el feedback de una respuesta incorrecta (US-05).

    Contenido: explicación conceptual, análisis del error, refuerzo positivo
    y tema a repasar. Usa ExpansionPanel dentro de ExpansionPanelList
    (equiv. st.expander) con tarjeta blanca y acento índigo en header.
    """

    def __init__(self, feedback: Feedback) -> None:
        content_rows: list[ft.Control] = []
        # Solo renderizar bloques no vacíos; todos tienen fallback pero se
        # respeta el diseño limpio si algún campo viniera vacío.
        if feedback.explanation:
            content_rows.append(_field_block("Explicación conceptual", feedback.explanation))
        if feedback.error_analysis:
            content_rows.append(_field_block("Análisis del error", feedback.error_analysis))
        if feedback.positive_reinforcement:
            content_rows.append(_field_block("Refuerzo positivo", feedback.positive_reinforcement))
        if feedback.suggestion_topic:
            content_rows.append(_field_block("Tema a repasar", feedback.suggestion_topic))

        if not content_rows:
            content_rows.append(
                ft.Text("Sin retroalimentación disponible.", size=13.5, color=_TEXT_MUTED)
            )

        content = ft.Container(
            content=ft.Column(content_rows, spacing=12),
            padding=ft.Padding(0, 8, 0, 12),
            bgcolor=_SURFACE,
        )

        header = ft.ListTile(
            leading=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=_ACCENT, size=20),
            title=ft.Text(
                f"Pregunta {feedback.question_id}",
                size=14,
                weight=ft.FontWeight.W_600,
                color=_TEXT_PRIMARY,
            ),
            subtitle=ft.Text(
                feedback.suggestion_topic or "Retroalimentación",
                size=12.5,
                color=_TEXT_MUTED,
            )
            if feedback.suggestion_topic
            else None,
        )

        super().__init__(
            header=header,
            content=content,
            bgcolor=_SURFACE,
            expanded=False,
        )
        self.feedback = feedback


def build_feedback_panels(feedbacks: list[Feedback]) -> ft.ExpansionPanelList | None:
    """Construye el ExpansionPanelList para la lista de feedbacks, o None si vacía."""
    if not feedbacks:
        return None
    return ft.ExpansionPanelList(
        controls=[FeedbackExpander(fb) for fb in feedbacks],
        elevation=0,
        spacing=8,
    )
