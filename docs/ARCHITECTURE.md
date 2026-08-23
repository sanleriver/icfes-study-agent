# Arquitectura del Sistema

Agente tutor adaptativo ICFES Saber Pro (LangGraph + Python). Este documento describe el sistema **construido**; los planes de ejecución viven en `docs/planning/`.

## 1. Vista general

El sistema es una aplicación **Flet** (migrada desde Streamlit — `archive/app_streamlit.py` deprecado) que conduce una sesión de práctica por sección del ICFES Saber Pro. El orquestador es un **grafo LangGraph** con estado tipado en Pydantic. La evaluación es **100% determinista** (Python); el LLM (Gemini) solo genera la retroalimentación de las respuestas incorrectas, con fallback determinista si falla. Docker monolito `python:3.14-slim-bookworm` (`Dockerfile:1`) expone Flet web en `8000`.

```
Flet (flet_app/main.py:9) — router + views + GraphRunner (async)
   │  page.session.store: graph_runner + thread_id + current_question
   ▼
Grafo LangGraph (src/graph.py:84)  ── checkpointer InMemorySaver + thread_id
   initialize_session → next_question ─┐ (interrupt: presenta pregunta)
       ▲                               │ (Command(resume=opcion) → reanuda)
       └───────────────────────────────┘
   → evaluate_session → generate_feedback → generate_summary → END
                              │
                              ▼
                 FeedbackProvider (src/providers/)
                 MockFeedbackProvider | GeminiFeedbackProvider

Docker: [ flet:8000 ]  (docker-compose.yml:1)  — monolito src+flet_app+data
         [ tests (profile) ] — pytest en contenedor
```

## 2. Componentes

| Capa | Módulo | Responsabilidad |
| :--- | :--- | :--- |
| Interfaz | `flet_app/` (`main.py:9`, `router.py:42`, `views/`, `state/graph_runner.py:18`) | Presentación Flet; estado en `page.session.store` + `SharedPreferences` (thread_id). Legacy `archive/app_streamlit.py` deprecado. |
| Orquestación | `src/graph.py` | Grafo LangGraph con `interrupt()` (human-in-the-loop). |
| Dominio | `src/models/` | Modelos Pydantic y esquema de estado (`SessionState`). |
| Núcleo determinista | `src/core/evaluation.py` | Evaluación de respuestas, puntuación y resumen por tema. |
| Feedback determinista | `src/core/feedback.py` | `fallback_feedback` (base del mock y fallback del LLM). |
| Datos | `src/data/` | Carga del banco (`loader.py`) e imágenes (`images.py`). |
| Proveedores | `src/providers/` | `FeedbackProvider` (ABC), `MockFeedbackProvider`, `GeminiFeedbackProvider`, factory. |
| Config | `src/config.py` | Carga de `.env` (`FEEDBACK_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`). |

## 3. Flujo end-to-end

1. **Configuración (US-07):** el usuario elige sección y número de preguntas. El formulario llama a `graph.invoke({"section":..., "num_questions":...}, {configurable:{thread_id}})`.
2. **Inicialización:** `initialize_session` muestrea aleatoriamente las preguntas de la sección con `random_sample` (respeta el edge case de agotamiento y deja aviso en `message`).
3. **Pregunta a pregunta (US-03):** `next_question` presenta la pregunta con `interrupt(question.model_dump("json"))` y pausa el grafo. La UI renderiza enunciado + imagen (`st.image` vía `image_source`) + opciones A–D. Al responder, la UI reanuda con `Command(resume=opcion)`; el nodo se re-ejecuta desde el inicio y acumula `AnswerRecord` en `answers` (reducer `operator.add`).
4. **Evaluación (US-04):** cuando no quedan preguntas, `evaluate_session` compara cada opción contra `correct_option` y calcula puntuación.
5. **Feedback (US-05):** `generate_feedback` invoca el `FeedbackProvider` inyectado únicamente para las respuestas incorrectas.
6. **Resumen (US-06):** `generate_summary` construye puntuación total y desempeño por tema.

## 4. Estado y reducers (SessionState)

`src/models/session.py` define el esquema del grafo:

- `answers` usa el reducer `Annotated[list[AnswerRecord], operator.add]`: **acumula** sin sobrescribir.
- Los demás campos **sobrescriben**: `questions`, `results`, `feedbacks`, `summary`, `message`.
- Los nodos deben devolver **dicts de actualización parcial** (nunca mutar el estado completo).

## 5. Human-in-the-loop en LangGraph

- Cada pregunta se pausa con `interrupt(...)`; el config debe incluir `thread_id`.
- Se reanuda con `Command(resume=opcion)` usando el **mismo** `thread_id`.
- El checkpointer es `InMemorySaver` (en memoria del proceso; en Streamlit se conserva en `st.session_state["graph"]`).
- `record_answer` está fusionado en `next_question`: al reanudar, el nodo se re-ejecuta desde el inicio.
- Skills de referencia en `.agents/skills/` (fundamentals, persistence, human-in-the-loop).

## 6. Capa de proveedores de feedback

`src/providers/` implementa el contrato `FeedbackProvider.generate_feedback(question, result) -> Feedback`.

| Proveedor | Cuándo | Comportamiento |
| :--- | :--- | :--- |
| `MockFeedbackProvider` | `FEEDBACK_PROVIDER=mock` (default) | Determinista; delega en `fallback_feedback`; ignora la imagen. |
| `GeminiFeedbackProvider` | `FEEDBACK_PROVIDER=gemini` + clave | SDK `google-genai`, JSON validado con Pydantic (`FeedbackContent`), retry ×3 con exponential backoff, visión (`statement_image` → `inline_data`), y fallback determinista si falla o la salida es inválida. |

- El grafo **nunca** llama `fallback_feedback` directamente: `build_graph(feedback_provider=...)` inyecta el proveedor (por defecto mock para que los tests no dependan de API key).
- `create_feedback_provider(settings)` resuelve el proveedor desde `.env`.

### Cómo añadir un proveedor nuevo

1. Implementar `FeedbackProvider` en `src/providers/`.
2. Exponerlo en `src/providers/__init__.py`.
3. Resolverlo en `create_feedback_provider` (o inyectarlo directamente en `build_graph(feedback_provider=...)`).

## 7. Ciclo de vida en Flet (flet_app/)

- El estado persistente se guarda en `page.session.store` vía `SessionManager` (`flet_app/state/session_manager.py:13`): `graph_runner` (con `thread_id` en `SharedPreferences`), `current_question`, `pending_answer`, `final_result`.
- `GraphRunner` (`flet_app/state/graph_runner.py:18`) ejecuta `graph.invoke`/`resume` en `asyncio.to_thread` para no bloquear el event loop de Flet.
- `router.py:42` + `render_route` gestiona `/` → `/question` → `/results`; `QuestionView` re-monta su ruta tras `resume` porque `push_route` a misma ruta no dispara `on_route_change`.
- "Nueva sesión" genera `new_thread()` con nuevo `thread_id` (descarta checkpointer previo).

## 7b. Ciclo de vida legacy Streamlit (archive/app_streamlit.py — deprecado)

- Ver `archive/README.md`. Estado en `st.session_state`: `graph`, `thread_id`, `pending`, `final`, `answered`, `message`. Se mantiene solo como referencia.

## 9. Docker (monolito)

- `Dockerfile:1` — `python:3.14-slim-bookworm` (`ARG PYTHON_VERSION=3.14`), multi-stage `deps→runtime`, non-root `appuser`, `EXPOSE 8000`, `HEALTHCHECK wget 8000`, `CMD ["flet","run","--web","--host","0.0.0.0","--port","8000","flet_app/main.py"]`.
- `docker-compose.yml:1` — servicio `flet` (`8000:8000`, `env_file:.env`), `tests` (profile).
- `docker-compose.override.yml` — bind-mounts `src/`, `flet_app/`, `data/` para hot-reload en dev.
- `.dockerignore` excluye `.venv`, `__pycache__`, `.env`, `docs/`, `.git`.

## 8. Convenciones clave

- Campos de `Question` en inglés (`topic`, `statement`, `options`, `statement_image`, `correct_option`); docstrings y mensajes de UI en español.
- Evaluación y puntuación siempre deterministas en Python; el LLM solo genera feedback.
- Gemini usa el SDK `google-genai` (`from google import genai`); `google-generativeai` está deprecado.
- 5 secciones fijas (`src/models/section.py`); opciones A–D estrictas en `Question`.