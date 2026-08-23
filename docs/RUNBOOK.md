# Runbook — Ejecución y configuración

Guía operativa del agente tutor ICFES Saber Pro (entorno **Windows + PowerShell**, Python 3.14).

## 1. Requisitos

- Windows + PowerShell.
- Python 3.14 instalado.
- Entorno virtual `.venv` con dependencias (`requirements.txt`).

## 2. Instalación

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> No existe `pyproject.toml`; las dependencias se declaran en `requirements.txt`. Nunca usar `.venv/bin/...`.

## 3. Configuración (`.env`)

| Variable | Valor | Descripción |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | (vacío por defecto) | Clave de Gemini para el proveedor real. |
| `FEEDBACK_PROVIDER` | `mock` (default) \| `gemini` | Selecciona el proveedor de feedback. |
| `GEMINI_MODEL` | `gemini-3.5-flash` (default) | Modelo usado por `GeminiFeedbackProvider`. |

- Con `mock` no se necesita clave; la app y los tests funcionan sin conexión.
- Con `gemini` sin `GEMINI_API_KEY`, la app muestra un error y el proveedor se sustituye por el mock; `create_feedback_provider` también lanza `ValueError`.

## 4. Ejecutar la app

### 4a. Local sin Docker (Flet)

```powershell
.\.venv\Scripts\flet.exe run --web flet_app/main.py   # web: http://localhost:8550
# o desktop:
.\.venv\Scripts\python.exe flet_app/main.py
```

> `archive/app_streamlit.py` es la UI Streamlit deprecada (ver `docs/planning/docker/PLAN_DOCKER.md`). No se usa en Docker.

### 4b. Con Docker (recomendado)

```powershell
docker compose up --build              # Flet web en http://localhost:8000
# dev con hot-reload (usa docker-compose.override.yml automáticamente):
docker compose up --build
# solo tests en contenedor:
docker compose --profile tests run --rm tests
docker compose down
```

Flujo esperado (Flet):

1. Seleccionar sección y número de preguntas → **Iniciar sesión**.
2. Responder las preguntas una a una (A–D). Si la pregunta tiene imagen, se muestra junto al enunciado (`flet_app/views/question_view.py:220` `image_source`).
3. Al final: métricas de puntaje, desempeño por tema y feedback de las incorrectas (expanders).

## 5. Ejecutar los tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q        # suite completa (64 tests)
.\.venv\Scripts\python.exe -m pytest tests\test_graph.py -q   # un archivo
```

## 6. Probar Gemini real (Fase 8)

1. Poner `GEMINI_API_KEY=<tu clave>` y `FEEDBACK_PROVIDER=gemini` en `.env`.
2. (Opcional) Ajustar `GEMINI_MODEL`.
3. Ejecutar la app y responder **mal** una pregunta **con imagen** (p. ej. sección Razonamiento Cuantitativo: `RQ-002`/`RQ-003`).
4. Verificar en el expander de feedback:
   - Que `explicación`/`análisis del error` tengan texto **pedagógico del LLM** (no el texto genérico del fallback, que viene de `key_points`).
   - Que estén los 4 campos del `Feedback` (`explanation`, `error_analysis`, `positive_reinforcement`, `suggestion_topic`).
   - Que la imagen se haya incluido en la llamada de visión (si el feedback menciona datos de la gráfica/bolsa, la visión funcionó).
5. Si la salida es mala o falla: revisar el prompt en `src/providers/gemini.py` (`_build_prompt`), el modelo (`GEMINI_MODEL`) o el esquema `FeedbackContent`.

> Si Gemini devuelve una respuesta bloqueada (safety) o sin texto, `response.text` es `None` y el proveedor cae automáticamente en `fallback_feedback` (la sesión no se rompe).

## 7. Solución de problemas

| Problema | Causa probable | Acción |
| :--- | :--- | :--- |
| `ValueError: FEEDBACK_PROVIDER=gemini requiere GEMINI_API_KEY` | `.env` sin clave. | Poner la clave o volver a `FEEDBACK_PROVIDER=mock`. |
| Feedback genérico (parece fallback) | Fallo/validación de Gemini o `mock` activo. | Verificar `FEEDBACK_PROVIDER`, clave, modelo y log de excepciones. |
| "Imágenes locales inexistentes" al cargar | `validate_image_references` detectó una ruta rota. | Comprobar `data/images/` y el campo `statement_image` del banco. |
| La app muestra el mismo formulario | Cambios de vista sin `st.rerun()`. | No debe pasar con el código actual; revisar `start_session`/`submit_answer`/`reset_session`. |
| Tests lentos o que fallan por red | Proveedor real activo durante la suite. | Los tests inyectan `MockFeedbackProvider`; no dependen de `.env` ni de la red. |