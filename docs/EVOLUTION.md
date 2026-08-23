# Roadmap de Evolutivos

Ideas de mejora sobre el sistema **actual**, con punteros al código para que un agente que retome el proyecto sepa por dónde empezar. Ordenadas de menor a mayor esfuerzo.

## 1. Dificultad adaptativa (muy solicitado)

- **Estado:** el MVP es fijo (`num_questions`, sin dificultad).
- **Punteros:** `Question` no tiene campo de dificultad; `random_sample` en `src/data/loader.py`; `initialize_session` en `src/graph.py`.
- **Qué hacer:** añadir `difficulty` a `Question` y al banco, y un selector adaptativo en `initialize_session` (o un nodo nuevo) que elija preguntas según el desempeño previo del estudiante.

## 2. Persistencia e historial por estudiante

- **Estado:** el checkpointer es `InMemorySaver` (`src/graph.py`) y el estado vive solo en `st.session_state` (`app.py`); al recargar se pierde todo.
- **Punteros:** `build_graph` (checkpointer), `app.py:init_state`, `docs/ARCHITECTURE.md` §4.
- **Qué hacer:** sustituir el checkpointer por `SqliteSaver`/`PostgresSaver` (persistencia de LangGraph) y/o guardar resúmenes de sesiones en una base de datos. Ver skill `langgraph-persistence`.

## 3. Más tipos de pregunta y banco más grande

- **Estado:** 20 preguntas (4 por sección), opciones A–D y `statement_image`.
- **Punteros:** `data/questions.json`, `src/models/question.py`, `src/data/loader.py`.
- **Qué hacer:** ampliar el banco, añadir tipos (selección múltiple, completar, etc.) — esto requeriría extender `Question`/`AnswerRecord` y la evaluación en `src/core/evaluation.py`.

## 4. Evaluar la calidad del feedback del LLM

- **Estado:** `GeminiFeedbackProvider` valida solo la forma (JSON + Pydantic); no hay evaluación de calidad ni retroalimentación sobre el feedback.
- **Punteros:** `src/providers/gemini.py` (`_build_prompt`, `_parse_response`), `docs/specs/01_specification.md` US-05.
- **Qué hacer:** añadir un modo de evaluación (otro LLM o rúbrica) que puntúe el feedback; metricas en el resumen o en un reporte.

## 5. Configuración más fina de la sesión

- **Estado:** sección + número de preguntas.
- **Punteros:** `app.py:show_config`, `src/models/session.py` (`SessionState`).
- **Qué hacer:** tiempo límite, mezclar secciones, modo examen (sin feedback inmediato), historial de intentos por tema.

## 6. Autenticación y multi-usuario

- **Estado:** sin usuarios; sesiones anónimas.
- **Punteros:** `app.py`, `SessionState`.
- **Qué hacer:** añadir login, asociar sesiones a un usuario y habilitar persistencia real (§2). Requiere pasar de `InMemorySaver` a un store compartido.

## 7. Streaming y experiencia en tiempo real

- **Estado:** el feedback llega completo al final (bloqueante).
- **Punteros:** `src/providers/gemini.py` (`_request_with_retry`), `app.py:show_results`.
- **Qué hacer:** usar `generate_content_stream` y mostrar el feedback incremental en Streamlit (`st.write_stream`).

## 8. Cierre pendiente (Fases 8–9)

- Probar Gemini real end-to-end y ajustar prompt/esquema (`docs/RUNBOOK.md` §6).
- Inicializar control de versiones (git) y commit inicial.
- Validación final de la suite y casos límite.

## Criterios de entrada para un evolutivo

1. Leer `AGENTS.md` (entry-point del agente) y `docs/ARCHITECTURE.md`.
2. Mantener el determinismo: evaluación y puntuación siempre en `src/core/`; el LLM solo feedback.
3. Respetar convenciones: campos en inglés, docstrings en español, nodos que devuelven dicts parciales, decisiones nuevas reflejadas en `docs/specs/01_specification.md`.
4. Correr `pytest tests -q` antes de terminar.