# Plan de Trabajo — Agente Tutor Adaptativo ICFES Saber Pro

> **HISTÓRICO (plan ejecutado).** Fases 0–7 completadas y verificadas con pytest (64 tests). Fase 8 (Gemini real) y Fase 9 (cierre) pendientes. Para la arquitectura y guías del sistema **construido** ver `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md` y `docs/RUNBOOK.md`.

**Decisiones de diseño:**
- Banco de preguntas estructurado por las 5 secciones del examen: Lectura Crítica, Razonamiento Cuantitativo, Competencias Ciudadanas, Comunicación Escrita e Inglés.
- El usuario elige la sección a estudiar y el número de preguntas de la sesión.
- Selección aleatoria de preguntas dentro de la sección elegida.
- Las preguntas se presentan una a una; al final de todas las respuestas se evalúa y se genera feedback de las respuestas incorrectas.
- MVP simplificado: sin dificultad adaptativa.
- Proveedor LLM con mock primero y Gemini después.
- Interfaz web con Streamlit.
- Suite de pruebas con pytest.

---

## Fase 0 — Fundaciones del proyecto
- Estructura de carpetas (`src/`, `data/`, `tests/`, `docs/`)
- Entorno virtual Python 3.14 + `requirements.txt`
- Dependencias: `langgraph`, `langchain`, `pydantic`, `streamlit`, `pytest`, `google-generativeai`
- `.env` con `GEMINI_API_KEY` (placeholder) + cargador de config
- Actualizar `docs/specs/01_specification.md` al nuevo flujo (secciones + evaluación final)
- ✅ **Entregable:** proyecto importa sin errores y spec coherente

## Fase 1 — Dominio tipado (Pydantic)
- `Section` (enum): `LECTURA_CRITICA`, `RAZONAMIENTO_CUANTITATIVO`, `COMPETENCIAS_CIUDADANAS`, `COMUNICACION_ESCRITA`, `INGLES`
- Modelos: `Question`, `SessionState`, `AnswerRecord`, `EvaluationResult`, `Feedback`, `Summary`
- `SessionState` incluye: `section`, `num_questions`, `questions[]`, `answers[]`, `results[]`, `feedbacks[]`, `summary`
- ✅ **Entregable:** modelos tipados con validación

## Fase 2 — Banco de preguntas por sección
- `data/questions.json` con **16–20 preguntas distribuidas entre las 5 secciones** (3–4 por sección)
- Cada pregunta: `id`, `section`, `topic`, `statement`, `options`, `correct_option`, `key_points`
- Loader: `get_questions_by_section(section)` y `random_sample(section, n)`
- ✅ **Entregable:** cargar y muestrear preguntas por sección

## Fase 3 — Núcleo determinista (sin LLM)
- `evaluate_session(answers)`: compara cada respuesta contra `correct_option` y clasifica correcta/incorrecta
- Identificación de respuestas incorrectas para feedback posterior
- Cálculo de puntuación (aciertos / total) para el resumen
- ✅ **Entregable:** funciones puras y testeables en `src/core/`

## Fase 4 — Grafo LangGraph
- Nodos: `initialize_session`, `next_question`, `evaluate_session`, `generate_feedback`, `generate_summary`
- Presentación por pregunta con `interrupt()` (human-in-the-loop): el nodo `next_question` pausa con la pregunta y espera `Command(resume=opcion)`. `record_answer` quedó fusionado en `next_question` (al reanudar el nodo se re-ejecuta desde el inicio). Requiere `thread_id` y checkpointer (InMemorySaver).
- Borde condicional: **¿quedan preguntas?** → continuar presentando o pasar a `evaluate_session`
- Feedback solo de las incorrectas (al final), luego resumen
- ✅ **Entregable:** `src/graph.py` con el flujo completo por sección

## Fase 5 — Proveedor LLM (mock primero) ✅
- Interfaz abstracta `FeedbackProvider` en `src/providers/` (`base.py`), usada por el nodo `generate_feedback` del grafo
- `MockFeedbackProvider` determinista (desarrollo/tests sin API key); delega en `fallback_feedback` e ignora la imagen
- `GeminiFeedbackProvider` (SDK `google-genai`): retry ×3 + exponential backoff, salida JSON validada con Pydantic, fallback determinista e integración de visión (`statement_image` → `inline_data` con bytes locales o URL descargada)
- `create_feedback_provider(settings)` resuelve el proveedor según `FEEDBACK_PROVIDER=mock|gemini`
- `build_graph(feedback_provider=...)` inyecta el proveedor (por defecto `MockFeedbackProvider` para tests)
- ✅ **Entregable:** feedback intercambiable vía config

## Fase 6 — Interfaz Streamlit ✅
- `app.py` (raíz): desplegable de sección (5 opciones) + número de preguntas
- Presenta las preguntas **una a una** (A/B/C/D) con `st.radio`; reanuda el grafo con `Command(resume=opcion)` y `thread_id`
- Si la pregunta tiene `statement_image`, se renderiza con `st.image` usando `image_source` (ruta local o URL)
- Al finalizar: métricas de puntaje, desempeño por tema y feedback de cada respuesta incorrecta (expanders)
- Estado persistente en `st.session_state` (grafo con checkpointer, `thread_id`, pregunta pendiente, resultado final)
- Proveedor de feedback resuelto con `create_feedback_provider()` desde `.env` (`FEEDBACK_PROVIDER=mock|gemini`)
- ✅ **Entregable:** `app.py` funcional con el mock (probado con `streamlit.testing.v1.AppTest`)

## Fase 7 — Suite de pruebas (pytest) ✅
- Muestreo aleatorio por sección (N preguntas, todas de la sección elegida)
- Evaluación determinista (correctas/incorrectas)
- Flujo completo del grafo: sección + N preguntas → evaluación → feedback de incorrectas → resumen
- Fallback ante fallo del LLM (a nivel de proveedor y end-to-end en el grafo)
- ✅ **Entregable:** `pytest` en verde (64 tests)

## Fase 8 — Integración real con Gemini
- Activar `GEMINI_API_KEY`, probar feedback real end-to-end, ajustar prompts/JSON schema
- ✅ **Entregable:** sesión completa funcionando con Gemini

## Fase 9 — Validación y cierre
- Correr toda la suite + revisar casos límite
- README con instrucciones
- ✅ **Entregable:** proyecto listo para ejecutar
