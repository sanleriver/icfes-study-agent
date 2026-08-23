from __future__ import annotations

import flet as ft

from flet_app.theme import BORDER as _BORDER
from flet_app.theme import SURFACE as _SURFACE
from flet_app.theme import TEXT_MUTED as _TEXT_MUTED
from flet_app.theme import TEXT_PRIMARY as _TEXT_PRIMARY


class MetricCard(ft.Container):
    """Tarjeta de métrica — valor destacado + label uppercase (US-06).

    Sigue los tokens del Design System «Académico sereno»:
    tarjeta blanca sobre fondo neutro, borde GREY_300 1.5px, radio 12,
    padding 16. El color del valor es paramétrico:
    - INDIGO_600 para puntaje (acento único)
    - GREEN_600 / RED_600 solo como semántica correcto/incorrecto
    """

    def __init__(
        self,
        label: str,
        value: str,
        value_color: str,
        *,
        expand: bool | int = True,
    ) -> None:
        super().__init__(
            content=ft.Column(
                [
                    ft.Text(
                        label.upper(),
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=_TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        value,
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=value_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=_SURFACE,
            border=ft.Border.all(1.5, _BORDER),
            border_radius=12,
            padding=16,
            alignment=ft.Alignment.CENTER,
            expand=expand,
        )
        # Exponer para inspección en tests / E2E sin romper encapsulado.
        self.label = label
        self.metric_value = value
        self.value_color = value_color
