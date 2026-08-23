# Layout Fullscreen — Config / Question / Results (maxWidth 900, centrado H)

> Spec para agente de implementación. Bindea a `.ulpi/design/DESIGN.md` — *Every screen must read as the same product if placed side by side.*

## 1. Resumen

Unificar `/`, `/question`, `/results` bajo un **shell fullscreen** idéntico: `View(bg=_BG)` → `Container(expand=True, bgcolor=_BG, padding=32)` → `Column(expand=True, scroll=AUTO, horizontal_alignment=CENTER, alignment=START)` → `Container(width=900, alignment=TOP_CENTER)` → contenido específico. Centrado **solo horizontal**, vertical `START` (anclado arriba). `maxWidth 900` uniforme sustituye `Config 520` y `Question 640` diferenciados.

## 2. User flows y estados

### Flujo primario

```
Config "/" (selección sección + N) → push "/question" → loop Q1..QN (resume) → "/results" → Nueva sesión → "/"
```

Branching: `N > disponible` → snack “Solo hay X disponibles”; `runner is None` → init; `runner exists` → new_thread; deep-link `/question` sin `graph_runner` → redirect `/`; `final_result exists` → redirect `/results`.

### Estados por vista

| Vista | Estado | Trigger | UI | A11y |
|-------|--------|---------|----|------|
| Config | empty | sin `section` | `start_button.disabled=True` | focus en dropdown |
| Config | filled | `on_select` Section | `availability_text` “X preguntas disponibles”, button enabled | aria-live polite |
| Config | loading | `on_start` click | `button = ProgressRing 20 + Preparando…`, disabled, `update()` | `aria-busy` |
| Config | error | `create_feedback_provider` / `GraphRunner` exception | `SnackBar RED_600` | role alert |
| Config | clamped | stepper <1 or >20, blur | `_apply_num clamp 1-20`, buttons disabled at bounds | — |
| Question | loading | `runner.invoke` / `resume` | (no visible, breve) | — |
| Question | question | `__interrupt__` con `q_data` | header `PREGUNTA i DE N` 11 BOLD + topic 12.5 + statement 16 + image 280 + 4 tiles + Responder disabled | tiles `role=button` |
| Question | selected | tile click | `tile.bgcolor=ACCENT_TINT`, `border 2 ACCENT`, button enabled | aria-selected |
| Question | submitting | `on_submit` is_last=false | `Enviando respuesta…` ring 20 | aria-busy |
| Question | calculating | `is_last=true` | `Calculando resultados…` ring 28 + overlay `visible=True`, card `opacity .55`, tiles `disabled opacity .6` | modal focus trap |
| Question | error | resume exception | SnackBar + reset button/tiles/overlay | — |
| Question | empty redirect | `get_final_result != None` o `runner is None` | `push_route /results` o `/` | — |
| Results | success | `summary` + `feedbacks` | header 28 BOLD + 3 MetricCard Row SPACE_BETWEEN + by_topic card + feedback ExpansionPanelList + Nueva sesión | — |
| Results | banner | `final.message` non-empty | `Container ACCENT_TINT border INDIGO_200` | — |
| Results | no_feedback | `feedbacks == []` | `CHECK_CIRCLE + ¡Excelente!` card | — |

Edge: refresh en `/question` pierde `page.session.store` si browser reload (Flet session volatile) → redirect `/`; offline → snack; `statement_image` missing → `image_source` None → no Image; `FLET_WEB` env vs `flet run --web` → ambos soportados (`main.py:36`).

## 3. Component specs

### 3.1 Shell común `FullscreenCenteredShell`

- **Propósito:** envolver cualquier vista product para paridad fullscreen.
- **Props:** `child: Control`, `max_width: int = 900`, `bg: Color = BG`, `padding: Padding = 32`
- **Estructura Flet:**
```python
ft.View(
    controls=[
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=child,
                        width=PAGE_MAX_WIDTH,  # 900
                        alignment=ft.Alignment.TOP_CENTER,
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # solo H
                alignment=ft.MainAxisAlignment.START,               # vertical arriba
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=PAGE_PADDING,  # 32
            bgcolor=BG,
            expand=True,
        )
    ],
    route="/... ",
    bgcolor=BG,
)
```
- **Variantes:** `ConfigShell`, `QuestionShell`, `ResultsShell` — misma estructura, solo `child` cambia.
- **Responsive:** `width=900` en viewport >964 (900+32*2) → centrado con 32 márgenes. Viewport <964 → Flet recorta; `Container` sin `clip` permite `scroll.AUTO` horizontal no deseado → asegurar `child` no excede viewport: `width=900` con `expand` en outer Column lo limita; en móvil (<600) el card ocupará `viewport -64`. Si Flet 0.86.5 no soporta `maxWidth`, usar `width=900` + `scroll` es suficiente (probado en web).
- **Estados:** `loading` no cambia shell; `error` SnackBar overlay fuera de shell.
- **A11y:** shell no añade tab stops.

### 3.2 ConfigView (`flet_app/views/config_view.py:64`)

- **Cambios:**
  - Import `PAGE_MAX_WIDTH, PAGE_PADDING` desde `theme.py`.
  - `content = Column([...header, section, availability, stepper, button...], spacing12, scroll NONE, expand False)` — ya no `expand True` (el shell lo hace).
  - `card = Container(content=content, width=900, bgcolor=SURFACE, border 1.5 BORDER, radius12, padding24)` — nuevo: envolver contenido en card blanca (antes era directo Column en Container BG). Esto alinea con Question/Results que usan `SURFACE` card.
  - `View` usa `FullscreenCenteredShell(card)`.
- **Props internas intactas:** `DROPDOWN_WIDTH 380` (centrado dentro de 900, deja 260 margen cada lado), `num_field width72`, stepper Row spacing8, `start_button height48 width 900-48*2? No — button expand dentro de card: `width=900-48` (852) o `expand True` en Row.
- **Interacción:** `on_select` → `update()` ya centrado; no cambia.
- **A11y:** dropdown `hint_text`, `leading_icon`, `on_select`.

### 3.3 QuestionView (`flet_app/views/question_view.py:105`)

- **Cambios:**
  - `_card width`: `640 → 900` (`theme.PAGE_MAX_WIDTH`). Actualizar `_card_overlay width 900` (`question_view.py:163` y `width 340` interno se mantiene).
  - `card_stack = Stack(controls=[_card, _overlay], width=900)` (antes 640).
  - `submit_button width`: `640-48=592 → 900-48=852` (`question_view.py:140`).
  - `content = Column([card_stack], horizontal_alignment=CENTER, scroll=AUTO, expand=True)` + outer `FullscreenCenteredShell` con `padding32` — quitar `Container(content=content, padding32)` interno y delegar a shell.
  - Mantener `image_control height280 BoxFit.CONTAIN border_radius12`.
  - `options_column spacing10` dentro de card 900 → tiles más anchos, mejor lectura.
- **Estados:** overlay `visible` y `card.opacity .55` siguen centrados sobre 900.
- **Responsive:** `card_stack width 900` en móvil se recorta → scroll horizontal no; Flet Column con `expand` permite que card se achique si `width` es fija. Alternativa: usar `Container(width=900, expand=False)` deja overflow; preferible `maxWidth` si disponible. Fallback: mantener `width=900` y confiar en `scroll=AUTO` vertical, horizontal no scrola porque Flet corta. Probar en 375px: card 900 excede → se necesita `width = min(900, viewport)`— Flet no tiene `min()`; usar `ResponsiveRow` con `col={"xs":12}` y `Container(col=12)` para que ocupe 100% en xs. Decisión: implementar `ResponsiveRow` si manual test falla, sino `width=900` simple.

### 3.4 ResultsView (`flet_app/views/results_view.py:164`)

- **Cambios:**
  - `content` (`Column` spacing10 scroll AUTO expand True) → envolver en `Container(width=900, alignment=TOP_CENTER)` + outer `Column(horizontal_alignment=CENTER, alignment=START)`.
  - `metrics_row` (`Row spacing12 SPACE_BETWEEN`) dentro de 900 → 3 `MetricCard` cada ~291 width (900-24)/3.
  - `by_topic_block` y `feedback_block` ya son `Container` con `border` → quedarán dentro de 900 sin cambio.
  - `new_session_button expand True` dentro de `Row` 900 → full-width 900.
  - Outer `View` ya `Container(padding32, expand)` → sustituir por shell.

### 3.5 Theme (`flet_app/theme.py:28`)

- **Add:** `PAGE_MAX_WIDTH = 900` (locked), `PAGE_PADDING = 32` ya existe.
- **Keep legacy compat:** `CARD_WIDTH = PAGE_MAX_WIDTH` (alias) para `from theme import CARD_WIDTH` no rompa.
- **No new palette:** usar tokens existentes `ACCENT`, `BG`, etc.

### 3.6 Main (`flet_app/main.py:12`)

- **Keep:** `page.window.width=900` coincide con `PAGE_MAX_WIDTH` — no cambiar.
- **Optional:** añadir `page.horizontal_alignment` try/except si se quiere centrar page-level, pero shell ya lo hace — no necesario.

## 4. Interacción y responsive

- **Desktop 1920:** 900 centrado → márgenes `BG` 510 cada lado (1920-900-64)/2 ≈ 493 + padding32 = simétrico.
- **Laptop 1366:** márgenes ~201 cada lado.
- **Tablet 768:** 900 >768 → card ocupa `768-64=704` (Flet recorta width fija 900, scroll horizontal evitado si se usa ResponsiveRow; si width fija, Flet mostrará overflow cortado — mitigar con ResponsiveRow).
- **Mobile 375:** card 900 → debe colapsar a `311` (375-64). **Solución:** usar `ResponsiveRow` con `col 12` + `Container(col={"xs":12,"md":10})` para que Flet ajuste ancho; o detectar `page.width` y sete `width = min(900, page.width-64)` en `build()`.

## 5. Design Pre-Flight gate

- [ ] Identity lock: `DESIGN.md` re-leído, `PAGE_MAX_WIDTH 900`, `RADIUS 12`, `ACCENT INDIGO_600` inmutables.
- [ ] Anti-slop: sin 3 cards iguales, sin glassmorphism, sin gradient text, sin Inter display, sin em-dash, sin nested cards (card dentro de shell no es nested — shell es BG, card es surface).
- [ ] State coverage: todos estados §2 cubiertos, incl. `clamped`, `deep-link redirect`, `overlay`.
- [ ] A11y: focus order, contrast AA (muted 4.6:1, accent 6.1:1), SnackBar role alert, ProgressRing semantics.
- [ ] Layout craft: variación dentro de identidad (3 shells idénticos, contenido varía), no deriva.
- [ ] Cognitive load: config simple (4 controles), question una tarea, results 3 métricas + 2 bloques.

## 6. Build handoff

- **Target agent:** `python-flet-engineer` (bespoke Flet). Si no disponible, `general` con nota “Flet 0.86.5, no React”.
- **Design system:** `bespoke (Flet)` — themear con `theme.py` tokens, no re-diseñar.
- **Instrucción delegada:** *“Implement exactly this spec. Theme the Flet theme with our locked tokens (`ACCENT`, `BG`, `PAGE_MAX_WIDTH=900`); do NOT redesign components. Use `FullscreenCenteredShell` with horizontal-only centering. Keep `DROPDOWN_WIDTH 380`, `BUTTON_HEIGHT 48`, `RADIUS 12`. Respect `prefers-reduced-motion`.”*
- **Archivos objetivo:**
  1. `flet_app/theme.py:30` → add `PAGE_MAX_WIDTH=900`
  2. `flet_app/views/config_view.py:183` → wrap `content` en `Container(width=900, bgcolor=SURFACE, ...)` + `FullscreenCenteredShell`
  3. `flet_app/views/question_view.py:153` → `_card width 900`, `_overlay width 900`, `submit_button width 852`, wrap en shell
  4. `flet_app/views/results_view.py:171` → wrap `content` en `Container(width=900)`
  5. `flet_app/main.py:12` → verify `window.width` 900 alignment
- **Aceptación:**
  - Visual: las 3 rutas fullscreen `bg BG`, contenido 900 centrado H, anclado arriba, `padding32`.
  - Config card blanca 900 con header 28, dropdown 380 centrado en 900, stepper centrado, button 48.
  - Question card 900 con statement 16, image 280, 4 tiles, button 852, overlay 900.
  - Results 900 con 3 metrics ROW, by_topic, feedback list, button full 900.
  - Tests: `pytest -q` 60 passed 5 skipped; `docker compose up --build` → `curl http://localhost:8000/ 200` + `health healthy`.
  - Responsive: viewport 375 → card `311` sin overflow horizontal (ResponsiveRow fallback si width fija falla).
