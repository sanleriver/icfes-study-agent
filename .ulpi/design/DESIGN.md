---
project: icfes_tutor
register: product
aesthetic_direction: Swiss / grid
color_strategy: restrained
design_system: bespoke (Flet)
design_variance: 4
motion_intensity: 3
visual_density: 4
---

## Design Read

Claro, reticular y sereno — una grilla suiza que ordena la evaluación sin ruido: confianza académica sobre novedad.

## Signature

**Grilla académica 900 centrada H.** Un único shell: viewport fullscreen `GREY_50` con `padding 32` y un contenedor central de `maxWidth 900` centrado solo horizontal (`horizontal_alignment=CENTER`, vertical `START`). Radio 12, borde 1.5 y surface blanca enmarcan la tarea; todo lo demás permanece quieto. Gastamos audacia en un solo lugar — la grilla — y mantenemos el resto disciplinado (regla “remove one accessory”). *Every screen must read as the same product if placed side by side.*

## Inspiration

Sin URLs de referencia aportadas. DNA sintetizado del brief + código existente (`flet_app/theme.py:15` “Académico sereno”): tomar retícula suiza, jerarquía 28 BOLD / 11 BOLD uppercase / 13-14 body, tint neutrals hacia índigo, un solo acento. Rechazado: purple→blue glow, cream/beige body, three equal cards, glassmorphism, em-dash crutch, Inter como display. Síntesis: no es clon de una referencia — es evolución del sistema existente hacia paridad fullscreen.

## Color (locked)

| role | OKLCH | hex | use | WCAG |
|------|-------|-----|-----|------|
| background | 0.98 0.005 260 | #F8F9FC | `BG` GREY_50 — viewport | text 15.2:1 |
| surface | 1.00 0.000 0 | #FFFFFF | `SURFACE` — cards, panels | text 15.2:1 |
| elevated | 1.00 0.000 0 | #FFFFFF | overlay `Calculando…` | — |
| text | 0.21 0.015 260 | #1A1D23 | `TEXT_PRIMARY` GREY_900 | on surface 15.2:1 AA |
| muted | 0.55 0.012 260 | #6B7280 | `TEXT_MUTED` GREY_500 — labels, hints | on surface 4.6:1 AA |
| subtle | 0.70 0.010 260 | #9CA3AF | captions secundarias | on surface 2.9:1 (large only) |
| border | 0.88 0.008 260 | #D1D5E0 | `BORDER` GREY_300 — 1.5px | UI 3:1 |
| accent | 0.45 0.22 270 | #4338CA | `ACCENT` INDIGO_600 — único acento 10% | on white 6.1:1 AA |
| accent_tint | 0.96 0.02 270 | #EEF2FF | `ACCENT_TINT` INDIGO_50 — selected tile | — |
| success | 0.55 0.18 145 | #16A34A | GREEN_600 — Correctas | on white 3.4:1 |
| danger | 0.55 0.22 25 | #DC2626 | RED_600 — Incorrectas, error | on white 4.5:1 AA |
| warning | 0.75 0.15 75 | #D97706 | amber — futuro | — |
| info | 0.55 0.12 240 | #2563EB | blue — banner info | — |

- Neutrals tinted +0.005–0.015 chroma hacia 260–270 (índigo).
- Distribución 60-30-10: background 60, surface 30, accent 10.
- Dark mode: no requerido (web/desktop light). Si se añade, re-derivar manteniendo tint.

## Type (locked)

| role | family | use | notes |
|------|--------|-----|-------|
| display | Roboto Bold 28 | `headline_large` — “Tutor ICFES Saber Pro”, “Resultados…” | tracking -0.02em, `text-wrap: balance`, fallback `Arial` metric-matched |
| label | Roboto Bold 11 uppercase | `label_small` — “SECCIÓN DEL EXAMEN”, “DESEMPEÑO POR TEMA” | letter-spacing 0.04em |
| body | Roboto Regular 13.5 | `body_medium` — statement 16, topic 12.5, opciones | measure max 75ch dentro de 900, `text-wrap: pretty` |
| utility | Roboto Regular 12.5 | `body_small` — hints, availability, snack | — |
| mono | — | no usado | — |

- Par en un eje: una familia (Roboto) en múltiples pesos (no serif+sans), justificado por `product` register y quiet body; se evita Inter (banned default) pero Roboto ya está en `theme.py:54 font_family="Roboto"` y es la fuente bloqueada — variación dentro de identidad, no deriva.
- Scale: 11 / 12.5 / 13.5 / 16 / 28.

## Scales (locked)

- **spacing:** `0, 4, 8, 12, 16, 24, 32, 48, 64` (4px base, `theme.py` PAGE_PADDING 32).
- **radius:** `12` único (`RADIUS 12`, `BORDER_WIDTH 1.5`, `BORDER_WIDTH_SELECTED 2`) — todo card/button/panel usa 12.
- **shadow:** `sm: 0 1 2 rgba(0,0,0,.06)`, `md: 0 4 16 rgba(0,0,0,.08)` solo para overlay `Calculando…` (`question_view.py:176`).
- **elevation z:** `base 0, dropdown 20, sticky 30, modalBackdrop 45, modal 50, toast 70`.
- **breakpoints:** `sm 640 · md 768 · lg 1024 (900 max) · xl 1280` — `PAGE_MAX_WIDTH 900` (< lg) para legibilidad.
- **motion:** `fast 150ms, base 300ms, emphasis 500ms`, easing `cubic-bezier(0.16,1,0.3,1)`, no bounce/elastic, exit 75% enter, honrar `prefers-reduced-motion`. Motivated only: progress-ring + overlay reveal.

## Voice

- **register:** plain, confident, académico — español, cercano, sin jerga.
- **action vocabulary (consistente):** `Iniciar sesión → Preparando sesión…`, `Responder → Enviando respuesta… / Calculando resultados…`, `Nueva sesión` (no “Reiniciar” mezclado). Snack `duración 4000ms`, error `RED_600`.

## Tokens estructurales (locked, de `theme.py`)

- `PAGE_MAX_WIDTH = 900` (nuevo, uniforme para `/`, `/question`, `/results`)
- `CARD_WIDTH = 640` deprecado → alias a `PAGE_MAX_WIDTH` (mantener compat `from theme import CARD_WIDTH`)
- `PAGE_PADDING = 32`, `DROPDOWN_WIDTH = 380`, `BUTTON_HEIGHT = 48`, `MIN/MAX/DEFAULT_QUESTIONS 1/20/5`
- `ACCENT=INDIGO_600`, `ACCENT_TINT=INDIGO_50`, `BG=GREY_50`, `SURFACE=WHITE`, `BORDER=GREY_300`, `TEXT_PRIMARY/MUTED`
