# 📋 Especificación Funcional (Spec-Driven Design)
**Feature:** Agente Tutor Adaptativo ICFES Saber Pro  
**Estado:** Listo para implementación  
**Nivel SDD:** Feature Specification

---

## 🎯 1. Intención y Propósito
El sistema debe proporcionar una experiencia de estudio guiada para estudiantes universitarios en Colombia que se preparan para la prueba **ICFES Saber Pro**. El agente actuará como un tutor personalizado que presenta una sesión de práctica por sección, evalúa las respuestas sin alucinaciones y genera explicaciones pedagógicas detalladas al final de la sesión.

---

## 📐 2. Principios de la Especificación (Guardarraíles)
1. **Determinismo de Evaluación:** El cálculo de respuesta correcta/incorrecta y la puntuación se basan en lógica dura (Python), no en evaluación probabilística del LLM.
2. **Generación Delimitada:** El LLM (Gemini) se limita a explicar el *porqué* conceptual de las respuestas incorrectas bajo una estructura JSON estricta (Pydantic).
3. **Persistencia Histórica:** Cada respuesta y resultado debe acumularse en el estado sin sobrescribir el historial anterior.
4. **Feedback Diferido:** La evaluación y el feedback se generan al final de la sesión, únicamente para las respuestas incorrectas.

---

## 🗂️ 3. Estructura del Examen

El ICFES Saber Pro se organiza en **5 secciones**. El banco de preguntas y las sesiones de estudio se estructuran siguiendo esta división:

| Sección | ID |
| :--- | :--- |
| Lectura Crítica | `LECTURA_CRITICA` |
| Razonamiento Cuantitativo | `RAZONAMIENTO_CUANTITATIVO` |
| Competencias Ciudadanas | `COMPETENCIAS_CIUDADANAS` |
| Comunicación Escrita | `COMUNICACION_ESCRITA` |
| Inglés | `INGLES` |

### Estructura de la Pregunta

Cada pregunta del banco se describe con: `id`, `section`, `topic`, `statement`, `options` (A–D), `correct_option`, `key_points` y opcionalmente `statement_image`.

- `statement_image` (opcional) acompaña al enunciado y puede ser:
  - Una **ruta local** relativa a `data/images/` (ej: `RQ-003.png`), resuelta por `image_source`.
  - Una **URL** (`http(s)://...`) que se renderiza directamente.
- En la presentación, si la pregunta tiene imagen, debe mostrarse junto al enunciado (`st.image` en Streamlit).
- Al generar feedback de una pregunta con imagen mediante Gemini, la imagen debe incluirse como entrada de visión junto al texto.

---

## 🔀 4. Casos de Uso y Criterios de Aceptación (GIVEN / WHEN / THEN)

### US-01: Configuración de la Sesión
* **GIVEN** que el estudiante inicia la aplicación,
* **WHEN** selecciona una sección (de las 5) y el número de preguntas `num_questions`,
* **THEN** el sistema debe inicializar el estado con `section`, `num_questions`, la lista de preguntas vacía, el historial de respuestas vacío y los resultados vacíos.

### US-02: Selección de Preguntas por Sección
* **GIVEN** una sesión configurada con `section` y `num_questions`,
* **WHEN** el agente ejecuta el nodo de selección,
* **THEN** debe elegir `num_questions` preguntas **aleatoriamente** de la sección seleccionada, sin repetir preguntas.

### US-03: Presentación de Preguntas una a una
* **GIVEN** una lista de preguntas seleccionadas,
* **WHEN** el agente presenta una pregunta,
* **THEN** el estudiante debe responderla (opción A, B, C o D) antes de pasar a la siguiente, acumulando la respuesta en `answers`.

### US-04: Evaluación Determinista de la Sesión
* **GIVEN** todas las preguntas respondidas por el estudiante,
* **WHEN** el agente ejecuta el nodo de evaluación,
* **THEN**:
  - Compara cada opción elegida contra `correct_option`.
  - Clasifica cada respuesta como correcta o incorrecta en `results`.
  - Calcula la puntuación de la sesión (aciertos / total).

### US-05: Retroalimentación Pedagógica de Respuestas Incorrectas
* **GIVEN** la evaluación de la sesión con al menos una respuesta incorrecta,
* **WHEN** el agente invoca la API del LLM al final de la sesión,
* **THEN** debe devolver, para **cada respuesta incorrecta**, un JSON con:
  - Explicación conceptual del tema.
  - Análisis del error/distractor elegido.
  - Refuerzo positivo y sugerencia de tema para repasar.
* **NOTA:** las respuestas correctas no generan retroalimentación individual.
* **NOTA:** la retroalimentación se produce a través de la interfaz `FeedbackProvider` (Fase 5), inyectada en `build_graph(feedback_provider=...)`: `MockFeedbackProvider` (determinista, sin API key) o `GeminiFeedbackProvider` (LLM con visión y fallback determinista).

### US-06: Resumen Final de la Sesión
* **GIVEN** la evaluación y el feedback de la sesión,
* **WHEN** el agente ejecuta el nodo de resumen,
* **THEN** debe presentar la puntuación total y el desempeño por tema de la sección estudiada.

### US-07: Interfaz Streamlit (Fase 6)
* **GIVEN** el estudiante inicia la aplicación (`app.py`),
* **WHEN** configura la sesión con el desplegable de sección (5 opciones) y el número de preguntas,
* **THEN** el sistema inicia la sesión en el grafo (thread_id persistido en `st.session_state`).
* **GIVEN** una sesión en curso,
* **WHEN** el estudiante responde una pregunta (A/B/C/D) con `st.radio`,
* **THEN** el sistema reanuda el grafo con `Command(resume=opcion)`, muestra la siguiente pregunta o el resumen final, e incluye la imagen del enunciado (`st.image`) cuando `image_source` devuelve una ruta o URL.
* **GIVEN** la sesión finalizada,
* **WHEN** el estudiante presiona "Nueva sesión",
* **THEN** se descarta el estado anterior (nuevo `thread_id`) y se vuelve a la configuración.

### US-08: Interfaz Flet de Escritorio (migración)
* **GIVEN** el estudiante abre la app (`flet run flet_app/main.py`),
* **WHEN** configura la sesión en `ConfigView` (dropdown de sección con icono por opción + stepper ±1 con caja de texto, rango 1–20),
* **THEN** el sistema guarda sección/N en el store de sesión, inicializa el grafo una sola vez
  (`GraphRunner` + `create_feedback_provider()`), persiste `thread_id` con el servicio
  `SharedPreferences` y navega a `/question`.
* Las rutas `/` → `/question` → `/results` son gestionadas por un router propio sobre
  `page.views` + `on_route_change`; el render inicial NO depende de `push_route("/")`
  (una ruta igual a la actual no dispara el evento).

**QuestionView y re-montaje tras responder (flet 0.86.5, Fase 6A refinado):** cada pregunta se muestra en
una tarjeta blanca `640px` centrada sobre fondo `GREY_50` con progreso «PREGUNTA K DE N» en label
uppercase, opciones A–D como filas clicables (borde índigo + tinte de acento al
seleccionarse) y botón Responder deshabilitado hasta elegir opción. `_render_question` envuelve la tarjeta en `Stack([_card, _card_overlay], width=640)` donde `_card_overlay` es velo `width 640, bgcolor white 0.68, visible False` con bloque interior `width 340, SURFACE, border 1.5 BORDER, padding 24, shadow 16` y `Column(ProgressRing 36/3.5 INDIGO_600 + "Calculando resultados…" 15 W_600 GREY_900 + "Evaluando respuestas y generando retroalimentación" 12.5 GREY_500)` centrado — velo solo sobre la tarjeta (no pantalla completa) con texto secundario, visible solo en la última pregunta. El re-montaje tras
responder llama directamente a la función `render_route` del router — NO usa
`push_route("/question")`, porque `Page.before_event` suprime `RouteChangeEvent` cuando
la ruta coincide con la última conocida (un push a la misma ruta nunca dispararía
`on_route_change` ni el `resume()` del grafo). Las navegaciones entre vistas distintas
usan `await page.push_route()`; las decisiones de navegación dentro de `build()` se
difieren con `page.run_task` para no solaparse con el render en curso. La imagen del
enunciado se resuelve con `image_source()`: URL tal cual o archivo local mapeado a
`flet_app/assets/images/<archivo>`. **Fase 6A — fin de sesión:** `SessionManager` persiste `total_questions` y `current_index` (`set_total_questions(total=len(questions))` y `set_current_index(answered+1)` tras cada `__interrupt__`, limpiados en `reset_session_state`); `QuestionView._on_submit` detecta `is_last = current_index >= total_questions` y si `is_last` muestra velo (`_card.opacity 0.55; _card_overlay.visible True`) + botón `ProgressRing 28/3 + "Calculando…" 14` (vs `20/2.5 + "Enviando respuesta…"` sin velo), y bloquea tiles (`disabled+opacity 0.6`) mientras el `resume()` final ejecuta `evaluate_session → generate_feedback → generate_summary` (relevante con `GeminiFeedbackProvider`); error restaura `opacity 1.0/visible False`.

**ResultsView (Fase 5, US-06/US-05 en Flet):** lee `SessionManager.get_final_result()` (`summary: Summary` + `feedbacks: list[Feedback]`). Muestra header propio (`EMOJI_EVENTS` índigo + headline 28px + `section.label`), banner `INDIGO_50` si `final["message"]` (agotamiento), fila de 3 métricas con `components/MetricCard` — Puntaje `INDIGO_600`, Correctas `GREEN_600`, Incorrectas `RED_600` (única excepción al acento único, semántica correcto/incorrecto) —, tarjeta de desempeño por tema (`DESEMPEÑO POR TEMA` 11px uppercase, filas `topic` 13.5px + `correct/total` 13px W_600 + `ProgressBar` índigo sobre `GREY_200` h=6 r=3; vacío → "No hubo preguntas respondidas."), y retroalimentación expandible por cada incorrecta (`components/FeedbackExpander` → `ExpansionPanel` con `ListTile` `LIGHTBULB_OUTLINE` índigo + 4 bloques 11px uppercase/13.5px: explicación conceptual, análisis del error, refuerzo positivo, tema a repasar; sin incorrectas → tarjeta `CHECK_CIRCLE` verde + "¡Excelente!..."). Botón «Nueva sesión» `FilledButton` altura 48 radio 12 full-width (`expand=True` en `Row`) hace el mismo reset que `ConfigView._on_start`: `manager.reset_session_state()` + `await runner.new_thread()` + `await page.push_route("/")` (US-07 sesiones consecutivas ilimitadas). Deep-link a `/results` sin `final_result` → `SnackBar` índigo + `page.run_task(push_route, "/")` diferido; errores → `logger.exception` + `SnackBar` roja, nunca falla en silencio.

**Design System «Académico sereno» (obligatorio para toda vista Flet, Fase 6A centralizado):**
un único color de acento `INDIGO_600` (tinte `INDIGO_50` para selección); fondo `GREY_50`,
tarjetas blancas con borde `GREY_300` y radio 12; jerarquía tipográfica 28 BOLD /
11 BOLD uppercase / 13–14 body; secciones distinguidas por icono Material (nunca por
color); patrones de entrada: `Dropdown` con `leading_icon` para listas de opciones y
stepper ±1 con caja de texto para números pequeños; botón primario full-width altura 48
disabled hasta entrada válida; estados obligatorios vacío/loading/aviso/error con
SnackBar + logging (nunca fallar en silencio); conteos reales del banco mostrados al
usuario. Tokens y `TextTheme` definidos en `flet_app/theme.py` (`ACCENT`, `BG`, `TEXT_PRIMARY`..., `CARD_WIDTH`, `BUTTON_HEIGHT`, `TEXT_THEME` con `headline_large` 28 BOLD/`label_small` 11 BOLD/`body_medium` 13.5/`body_small` 12.5 y `APP_THEME` con `color_scheme_seed="indigo"` + `PageTransitionsTheme.CUPERTINO` en windows/macos/linux), `views/config_view.py` los re-exporta para compatibilidad; tema global aplicado en `main.py:page.theme=APP_THEME`.

---

## ⚠️ 5. Casos Límite y Manejo de Errores (Edge Cases)

| Caso Límite | Comportamiento Esperado |
| :--- | :--- |
| **Agotamiento de Preguntas:** La sección tiene menos preguntas que `num_questions`. | El agente usa la cantidad máxima disponible de la sección y notifica al usuario. |
| **Respuesta Inválida:** El estudiante ingresa un valor diferente a A, B, C o D. | La capa de Presentación (Streamlit) debe validar y rechazar la entrada antes de actualizar el estado. |
| **Fallo de API LLM:** Timeout o error 5xx al consultar Gemini. | El agente debe reintentar hasta 3 veces con *exponential backoff*. Si persiste, genera un feedback fallback determinista predeterminado sin romper la sesión. |
| **Sección sin preguntas:** El banco no contiene preguntas para la sección elegida. | El agente fuerza la transición a `generate_summary` con un aviso y no presenta preguntas. |
| **Imagen inexistente:** La pregunta referencia una imagen local que no existe. | La carga del banco (`validate_image_references`) debe detectarla y lanzar un error claro antes de iniciar la sesión. |

---

## 🔌 6. Proveedor de Retroalimentación (Fase 5)

La generación de feedback es **intercambiable** mediante la interfaz `FeedbackProvider` (`src/providers/`), sin cambiar el grafo ni la evaluación.

| Proveedor | Comportamiento |
| :--- | :--- |
| `MockFeedbackProvider` | Determinista, para desarrollo/tests sin API key. Delega en `fallback_feedback` e ignora la imagen. |
| `GeminiFeedbackProvider` | LLM vía SDK `google-genai`. Salida JSON validada con Pydantic, retry ×3 con *exponential backoff* y fallback determinista si falla. Incluye la imagen (`statement_image`) como entrada de visión (`inline_data` con bytes locales o URL descargada). Modelo configurable vía `GEMINI_MODEL` (default `gemini-3.5-flash`). |

- `create_feedback_provider(settings)` resuelve el proveedor según `FEEDBACK_PROVIDER=mock|gemini` en `.env` (gemini sin `GEMINI_API_KEY` lanza error claro).
- El nodo `generate_feedback` del grafo recibe el proveedor por inyección: `build_graph(feedback_provider=...)`. Si no se indica, se usa `MockFeedbackProvider` para que la suite de tests sea determinista.
