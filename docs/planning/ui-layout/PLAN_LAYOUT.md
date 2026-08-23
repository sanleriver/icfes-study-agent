# Plan — Layout Fullscreen 900 (centrado H) — Config / Question / Results

> **Origen:** `.ulpi/design/DESIGN.md` (lock Swiss/grid, restrained, bespoke Flet) + `.ulpi/design/layout-fullscreen.md` (spec técnico).
> **Fecha:** 2026-08-23
> **Estado:** Plan generado, pendiente de `GO` para implementar (no se toca código aún por petición).

## Objetivo

Corregir percepción “ventana pequeña” en `/` y `/question` para que las 3 vistas ocupen **pantalla completa** como `/results`, con contenido **centrado solo horizontal** y **ancho máximo uniforme 900** (`theme.py:30 PAGE_MAX_WIDTH`).

- Config: mantener sencillez (no “súper grande”) — ahora 900 en lugar de propuesta previa 520, paridad con las otras dos.
- Question: card pasa de 640 → 900, mejor legibilidad enunciado/imagen/tiles.
- Results: envolver contenido actual full-bleed en 900 centrado.
- Centrado vertical **no** — anclado arriba (`alignment=START`), solo `horizontal_alignment=CENTER`.

## Diagnóstico

- `config_view.py:183` — `Column(expand)` sin wrapper centrado → controles anclados izquierda, `DROPDOWN_WIDTH 380` deja hueco.
- `question_view.py:153` — `_card width 640` + `Stack width 640` + `Column horizontal_alignment=CENTER` → isla 33% en 1920px, `page.window 900` limita desktop.
- `results_view.py:171` — `Column expand + Container padding32` → fullscreen nativo, referencia correcta.
- `theme.py:30` — `CARD_WIDTH 640` inconsistente entre vistas; `PAGE_PADDING 32` OK.
- `main.py:12` — `window.width 900` coincide con nuevo 900.

## Shell común propuesto

```python
ft.View(controls=[ft.Container(content=Column([Container(width=900)]))])
# outer Container expand bg BG padding32 → fullscreen
# inner Column horizontal_alignment=CENTER, alignment=START, scroll AUTO, expand True → solo H
# inner Container width=900 alignment TOP_CENTER → card
```

- Config: `content` (header+dropdown+stepper+button) → `Container(width=900, bgcolor=SURFACE, border 1.5, radius12, padding24)` → shell.
- Question: `_card 900`, `_overlay 900`, `submit_button 852` (900-48), `card_stack 900`, shell con `padding32`.
- Results: `content` (header+metrics+by_topic+feedback+button) → `Container(width=900)` → shell.

## Tokens

- `PAGE_MAX_WIDTH = 900` (nuevo, uniforme), `PAGE_PADDING=32`, `CARD_WIDTH` alias a 900 para compat.
- Palette `ACCENT INDIGO_600`, `BG GREY_50`, etc. sin cambio (restrained 60-30-10, WCAG AA).

## Flujos/estados

Mismo que spec: Config empty/filled/loading/error/clamped; Question loading/selected/submitting/calculating/overlay/error; Results success/banner/no_feedback. Edge deep-link `/question` sin `graph_runner` → redirect `/`.

## Responsive

- 1920 → márgenes 493 +32; 1366 → 201; 768 → card 704 (768-64); 375 → 311 (375-64).
- `width=900` fijo puede overflow en <964 → mitigar con `ResponsiveRow col 12` o `min(900, page.width-64)` en `build()` si test móvil falla.

## Archivos a tocar (en implementación)

1. `flet_app/theme.py:30` → `PAGE_MAX_WIDTH=900`
2. `flet_app/views/config_view.py:183` → wrap en card 900 + shell
3. `flet_app/views/question_view.py:153` → 640→900 + overlay 900 + button 852 + shell
4. `flet_app/views/results_view.py:171` → wrap en 900
5. `flet_app/main.py:12` → verificar `window.width 900` (no vertical center)

## Aceptación

- Visual 900 en 3 rutas, padding32, bg BG, centrado H, arriba, scroll AUTO.
- Tests `pytest -q` 60+5, `docker compose up --build` 200 healthy.
- Responsive <600 sin overflow horizontal.

## Siguiente paso

Esperar `GO` para ejecutar implementación (no se modifica código en este plan).
