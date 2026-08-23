"""Design System «Académico sereno» — fuente única de verdad (Fase 6A).

Tokens físicos y tema compartido por las 3 vistas + components.
No debe importar `flet_app.views` ni `flet_app.components` (hoja pura)
para evitar el ciclo `views ↔ components` visto en Fase 5.
"""

from __future__ import annotations

import flet as ft

# ------------------------------------------------------------------
# Tokens físicos
# ------------------------------------------------------------------
ACCENT = ft.Colors.INDIGO_600
ACCENT_TINT = ft.Colors.INDIGO_50
SURFACE = ft.Colors.WHITE
BG = ft.Colors.GREY_50
BORDER = ft.Colors.GREY_300
TEXT_PRIMARY = ft.Colors.GREY_900
TEXT_MUTED = ft.Colors.GREY_500

# Semántica permitida — única excepción al acento único
SUCCESS = ft.Colors.GREEN_600
ERROR = ft.Colors.RED_600

# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------
PAGE_MAX_WIDTH = 1140
CARD_WIDTH = PAGE_MAX_WIDTH  # alias legacy — mantener compat `from theme import CARD_WIDTH`
PAGE_PADDING = 32
RADIUS = 12
BORDER_WIDTH = 1.5
BORDER_WIDTH_SELECTED = 2
BUTTON_HEIGHT = 48
DROPDOWN_WIDTH = 380
MIN_QUESTIONS = 1
MAX_QUESTIONS = 20
DEFAULT_QUESTIONS = 5

# ------------------------------------------------------------------
# Tipografía — mapea regla 2 del Design System
# headline 28 BOLD → body 13-14 → nota 12.5 → label 11 BOLD uppercase
# ------------------------------------------------------------------
TEXT_THEME = ft.TextTheme(
    headline_large=ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
    label_small=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
    body_medium=ft.TextStyle(size=13.5, color=TEXT_PRIMARY),
    body_small=ft.TextStyle(size=12.5, color=TEXT_MUTED),
)

APP_THEME = ft.Theme(
    color_scheme_seed="indigo",
    font_family="Roboto",
    text_theme=TEXT_THEME,
)

# Transición Cupertino por defecto (Fase 6A) — también se aplica en main.py por seguridad.
try:
    _CUP = ft.PageTransitionTheme.CUPERTINO  # type: ignore[attr-defined]
    APP_THEME.page_transitions = ft.PageTransitionsTheme(
        windows=_CUP, macos=_CUP, linux=_CUP
    )
except Exception:
    pass

# Compatibilidad: re-export con nombres legacy _ACCENT etc. para
# imports antiguos (`from theme import _ACCENT`). Preferir nombres sin guión.
_ACCENT = ACCENT
_ACCENT_TINT = ACCENT_TINT
_SURFACE = SURFACE
_BG = BG
_BORDER = BORDER
_TEXT_PRIMARY = TEXT_PRIMARY
_TEXT_MUTED = TEXT_MUTED
