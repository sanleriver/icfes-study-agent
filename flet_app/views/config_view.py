from __future__ import annotations

import logging
from collections import Counter

import flet as ft

from flet_app.state.graph_runner import GraphRunner
from flet_app.state.session_manager import SessionManager
from src.data.loader import load_questions
from src.models import Section
from src.providers import create_feedback_provider

logger = logging.getLogger(__name__)

_AVAILABLE: Counter[Section] = Counter(q.section for q in load_questions())

# Re-export desde theme.py — única fuente de verdad (Fase 6A).
# Mantener nombres _ACCENT etc. para compatibilidad con imports existentes
# (`from flet_app.views.config_view import _ACCENT`).
from flet_app.theme import ACCENT as _ACCENT
from flet_app.theme import ACCENT_TINT as _ACCENT_TINT
from flet_app.theme import BG as _BG
from flet_app.theme import BORDER as _BORDER
from flet_app.theme import DEFAULT_QUESTIONS as _DEFAULT_QUESTIONS
from flet_app.theme import DROPDOWN_WIDTH as _DROPDOWN_WIDTH
from flet_app.theme import MAX_QUESTIONS as _MAX_QUESTIONS
from flet_app.theme import MIN_QUESTIONS as _MIN_QUESTIONS
from flet_app.theme import SURFACE as _SURFACE
from flet_app.theme import TEXT_MUTED as _TEXT_MUTED
from flet_app.theme import TEXT_PRIMARY as _TEXT_PRIMARY

_SECTION_ICONS: dict[Section, str] = {
    Section.LECTURA_CRITICA: ft.Icons.MENU_BOOK,
    Section.RAZONAMIENTO_CUANTITATIVO: ft.Icons.CALCULATE,
    Section.COMPETENCIAS_CIUDADANAS: ft.Icons.BALANCE,
    Section.COMUNICACION_ESCRITA: ft.Icons.EDIT_NOTE,
    Section.INGLES: ft.Icons.TRANSLATE,
}


class ConfigView:
    """Pantalla de configuración de sesión — dirección 'Académico sereno'.

    Selección de sección (dropdown con icono por sección), número de preguntas
    (stepper ±1 con caja de texto) e inicio de la sesión del grafo
    (GraphRunner + proveedor de feedback).
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.manager = SessionManager(page)
        self.start_button: ft.FilledButton | None = None
        self.availability_text: ft.Text | None = None
        self.section_dropdown: ft.Dropdown | None = None
        self.num_field: ft.TextField | None = None
        self.decrement_button: ft.OutlinedIconButton | None = None
        self.increment_button: ft.OutlinedIconButton | None = None

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    async def build(self) -> ft.View:
        header = ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE, size=28),
                    bgcolor=_ACCENT,
                    border_radius=ft.BorderRadius.all(14),
                    padding=14,
                ),
                ft.Column(
                    [
                        ft.Text(
                            "Tutor ICFES Saber Pro",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=_TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "Prepara el examen con sesiones de práctica adaptativa",
                            size=13.5,
                            color=_TEXT_MUTED,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            spacing=16,
        )

        self.section_dropdown = ft.Dropdown(
            width=_DROPDOWN_WIDTH,
            hint_text="Selecciona una sección…",
            options=[
                ft.DropdownOption(key=s.value, text=s.label, leading_icon=_SECTION_ICONS[s])
                for s in Section
            ],
            on_select=self._on_section_selected,
        )

        self.availability_text = ft.Text("", size=12.5, color=_TEXT_MUTED)

        self.num_field = ft.TextField(
            value=str(_DEFAULT_QUESTIONS),
            width=72,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            content_padding=ft.Padding(0, 14, 0, 14),
            on_blur=lambda _: self._normalize_num(),
        )
        self.decrement_button = ft.OutlinedIconButton(
            icon=ft.Icons.REMOVE,
            icon_color=_TEXT_PRIMARY,
            on_click=lambda _: self._bump_num(-1),
        )
        self.increment_button = ft.OutlinedIconButton(
            icon=ft.Icons.ADD,
            icon_color=_TEXT_PRIMARY,
            on_click=lambda _: self._bump_num(1),
        )
        stepper = ft.Row(
            [
                self.decrement_button,
                self.num_field,
                self.increment_button,
            ],
            spacing=8,
        )

        self.start_button = ft.FilledButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.PLAY_ARROW, size=20),
                    ft.Text("Iniciar sesión", weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            ),
            height=48,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            disabled=True,
            on_click=self._on_start,
        )

        content = ft.Column(
            [
                header,
                ft.Container(height=10),
                ft.Text(
                    "SECCIÓN DEL EXAMEN",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=_TEXT_MUTED,
                ),
                self.section_dropdown,
                ft.Row(
                    [
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=15, color=_TEXT_MUTED),
                        self.availability_text,
                    ],
                    spacing=6,
                ),
                ft.Container(height=6),
                ft.Text(
                    "NÚMERO DE PREGUNTAS",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=_TEXT_MUTED,
                ),
                stepper,
                ft.Container(height=10),
                self.start_button,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.View(
            controls=[ft.Container(content=content, padding=32, bgcolor=_BG, expand=True)],
            route="/",
            bgcolor=_BG,
        )

    # ------------------------------------------------------------------
    # Manejadores internos
    # ------------------------------------------------------------------

    def _on_section_selected(self, event: ft.ControlEvent) -> None:
        """Guarda la sección elegida y actualiza nota + botón."""
        key = getattr(event.control, "value", None)
        section = Section(key) if key else None
        assert self.availability_text is not None
        if section is None:
            self.availability_text.value = ""
        else:
            available = _AVAILABLE.get(section, 0)
            plural = "" if available == 1 else "s"
            self.availability_text.value = (
                f"{available} pregunta{plural} disponible{plural} "
                f"en el banco para esta sección."
            )
        assert self.start_button is not None
        self.start_button.disabled = section is None
        self.page.update()

    def _read_num(self) -> int:
        """Lee el número de la caja; devuelve el último válido si hay basura."""
        raw = (self.num_field.value or "").strip() if self.num_field else ""
        return int(raw) if raw.isdigit() else _DEFAULT_QUESTIONS

    def _apply_num(self, value: int) -> None:
        """Aplica un valor clamp 1-20 y sincroniza caja + botones."""
        n = max(_MIN_QUESTIONS, min(_MAX_QUESTIONS, int(value)))
        assert self.num_field is not None
        self.num_field.value = str(n)
        assert self.decrement_button is not None and self.increment_button is not None
        self.decrement_button.disabled = n <= _MIN_QUESTIONS
        self.increment_button.disabled = n >= _MAX_QUESTIONS
        self.page.update()

    def _bump_num(self, delta: int) -> None:
        """Incrementa/decrementa en 1 desde el valor actual de la caja."""
        self._apply_num(self._read_num() + delta)

    def _normalize_num(self) -> None:
        """Normaliza la caja al salir del campo (vacío/inválido → válido)."""
        self._apply_num(self._read_num())

    def _show_snack(self, message: str, error: bool = False) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_600 if error else _ACCENT,
                duration=4000,
            )
        )

    async def _on_start(self, _) -> None:
        """Valida, inicializa el grafo si hace falta y navega a /question."""
        assert self.section_dropdown is not None
        raw_key = self.section_dropdown.value
        if not raw_key:
            return
        section = Section(raw_key)
        num_value = self._read_num()

        button = self.start_button
        assert button is not None

        button.disabled = True
        button.content = ft.Row(
            [
                ft.ProgressRing(width=20, height=20, stroke_width=2.5),
                ft.Text("Preparando sesión…", weight=ft.FontWeight.W_600),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            tight=True,
        )
        self.page.update()

        try:
            available = _AVAILABLE.get(section, 0)
            if num_value > available > 0:
                self._show_snack(
                    f"Solo hay {available} preguntas disponibles para "
                    f"{section.label}; se usarán todas."
                )

            # Nueva sesión: descarta el estado por-sesión de la sesión
            # anterior (US-07) para permitir sesiones ilimitadas.
            self.manager.reset_session_state()
            self.manager.set_section(section)
            self.manager.set_num_questions(num_value)

            runner = self.manager.get_graph_runner()
            if runner is None:
                provider = create_feedback_provider()
                runner = GraphRunner(self.page)
                await runner.initialize(provider)
                self.manager.set_graph_runner(runner)
            else:
                # Re-invocar un thread completado corruptiría la sesión
                # (answers viejos desfasan los índices de next_question):
                # cada sesión explícita exige thread_id nuevo.
                await runner.new_thread()

            # Handler async: usar push_route (navigate es el wrapper sync).
            await self.page.push_route("/question")
        except Exception:
            logger.exception("Error iniciando la sesión de práctica")
            self._show_snack(
                "No se pudo iniciar la sesión. Revisa la consola para más detalles.",
                error=True,
            )
            button.disabled = False
            button.content = ft.Row(
                [
                    ft.Icon(ft.Icons.PLAY_ARROW, size=20),
                    ft.Text("Iniciar sesión", weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            )
            self.page.update()
