# AGENTS.md

Agente tutor adaptativo ICFES Saber Pro (LangGraph + Python). Documentos de referencia obligatorios: `README.md` (visión general y quickstart), `docs/ARCHITECTURE.md` (arquitectura real del sistema), `docs/DATA_MODEL.md` (modelos Pydantic y banco), `docs/RUNBOOK.md` (ejecución/configuración), `docs/specs/01_specification.md` (spec funcional, fuente de verdad de comportamiento). Los planes de ejecución ya completados viven en `docs/planning/` (históricos): `docs/planning/PROJECT_PLAN.md` (fases) y `docs/planning/PLAN_IMAGENES.md` (soporte de imágenes).

## Entorno y comandos

- **Windows + PowerShell.** No uses `.venv/bin/...`. Siempre invoca el intérprete del venv como `.\.venv\Scripts\python.exe`.
- **Python 3.14.6** en `.venv`. No hay `pyproject.toml`; las dependencias viven en `requirements.txt` (instalar con `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`).
- Ejecutar toda la suite: `.\.venv\Scripts\python.exe -m pytest tests -q` (actualmente 64 tests).
- Ejecutar un archivo de test: `.\.venv\Scripts\python.exe -m pytest tests\test_models.py -q`.
- **El repo NO es git todavía** (no hay `.git`). No asumas ramas/history.
- Sin linter/typecheck configurado. La verificación es pytest.

## Arquitectura

- `src/` es el paquete raíz: importar como `from src.models import ...` (nunca `import models`). `tests/conftest.py` inyecta la raíz del proyecto en `sys.path`.
- `src/models/` — dominios Pydantic. `SessionState` (`session.py`) es el **esquema de estado del grafo LangGraph**: `answers` usa reducer `Annotated[list[AnswerRecord], operator.add]` para acumular sin sobrescribir; los demás campos sobrescriben. Los nodos deben devolver dicts de actualización parcial, no mutar y retornar el estado completo.
- `src/data/loader.py` — banco en `data/questions.json`. `random_sample(section, n)` respeta el edge case de agotamiento (devuelve las disponibles si la sección tiene menos de `n`).
- `src/data/images.py` — imágenes de preguntas. `IMAGES_DIR = data/images`; `image_source(q)` devuelve la URL tal cual, la ruta local resuelta contra `IMAGES_DIR`, o `None`. `Question.statement_image` acepta ruta local o URL. `validate_image_references()` valida que las rutas locales existan.
- `src/core/evaluation.py` — lógica determinista (Fase 3): `evaluate_session(questions, answers)`, `incorrect_question_ids(results)`, `build_summary(section, questions, results)`.
- `src/core/feedback.py` — `fallback_feedback(question, result)` feedback determinista (fallback del LLM).
- `src/providers/` — capa de proveedores de feedback (Fase 5): `FeedbackProvider` (ABC en `base.py`), `MockFeedbackProvider` (`mock.py`, determinista, delega en `fallback_feedback`), `GeminiFeedbackProvider` (`gemini.py`, SDK `google-genai` con retry ×3 + exponential backoff, JSON validado con Pydantic y fallback; visión con `inline_data` para `statement_image` local o URL) y `create_feedback_provider(settings)` (resuelve `FEEDBACK_PROVIDER=mock|gemini`). `FeedbackContent` (schema JSON del LLM, sin `question_id`) vive en `gemini.py`.
- `src/graph.py` — grafo LangGraph (Fase 4) con `interrupt()` (human-in-the-loop): cada pregunta se presenta con `interrupt(question.model_dump(...))` y se reanuda con `Command(resume=opcion)`. Requiere `thread_id` en el config y checkpointer (InMemorySaver). `record_answer` está fusionado en el nodo `next_question` (al reanudar el nodo se re-ejecuta desde el inicio). Nodos: `initialize_session`, `next_question`, `evaluate_session`, `generate_feedback`, `generate_summary`. `build_graph(feedback_provider=...)` inyecta el proveedor (Fase 5); por defecto `MockFeedbackProvider` para que los tests no dependan de API key. El nodo `generate_feedback` se crea con `build_generate_feedback_node(provider)`.
- `src/config.py` — carga `.env` con pydantic-settings. `FEEDBACK_PROVIDER=mock|gemini`, `GEMINI_API_KEY` y `GEMINI_MODEL` (default `gemini-3.5-flash`).
- `app.py` (raíz) — interfaz Streamlit (Fase 6). Estado persistente en `st.session_state` (grafo compilado con checkpointer, `thread_id`, pregunta pendiente `pending`, resultado `final`, aviso `message`). Configura sección + `num_questions`, presenta preguntas una a una con `st.radio` + `Command(resume=opcion)`, renderiza la imagen con `st.image` vía `image_source`, y muestra métricas + desempeño por tema + feedback en expanders. El proveedor se resuelve con `create_feedback_provider()`; los cambios de vista usan `st.rerun()`.

## Convenciones y gotchas

- **Gemini:** usar el SDK `google-genai` (`from google import genai`). `google-generativeai` está deprecado — no reintroducirlo.
- **Evaluación determinista:** correcto/incorrecto y puntuación son lógica dura en Python; el LLM solo genera feedback. El feedback de respuestas incorrectas se genera al final de la sesión.
- **Proveedores de feedback:** el grafo nunca llama `fallback_feedback` directamente; el nodo `generate_feedback` usa el `FeedbackProvider` inyectado (`build_graph(feedback_provider=...)`). Nuevos proveedores deben implementar `FeedbackProvider` en `src/providers/` y exponerse en `create_feedback_provider`.
- **5 secciones** en `Section` (`src/models/section.py`): `LECTURA_CRITICA`, `RAZONAMIENTO_CUANTITATIVO`, `COMPETENCIAS_CIUDADANAS`, `COMUNICACION_ESCRITA`, `INGLES`. Toda pregunta del banco debe pertenecer a una de ellas.
- `Question` exige `options` con claves exactamente A–D y `correct_option` dentro de ese rango (validado en Pydantic). Los campos de `Question` están en inglés (`topic`, `statement`, `options`, `statement_image`).
- Las decisiones de diseño nuevas deben reflejarse en `docs/specs/01_specification.md` (no solo en código).
- `.env` y `.venv` están en `.gitignore`; no commitear secretos (aunque aún no hay git, mantener el `.gitignore` actualizado).

## Skills disponibles

- `.agents/skills/` contiene skills de LangGraph (fundamentals, persistence, human-in-the-loop, cli). Cargar `langgraph-fundamentals` antes de escribir/editar código del grafo.