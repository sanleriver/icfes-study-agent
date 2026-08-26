# Agente Tutor Adaptativo ICFES Saber Pro

Tutor de práctica para la prueba **ICFES Saber Pro**: presenta una sesión de preguntas por sección, evalúa las respuestas de forma determinista y genera retroalimentación pedagógica (mock o LLM Gemini) únicamente para las respuestas incorrectas. Interfaz web con **Flet** (migrado desde Streamlit, ver `archive/app_streamlit.py`) y flujo de agente con **LangGraph** (human-in-the-loop).

## Estado del proyecto

- **Fases 0–7 completadas** (config, modelos Pydantic, banco de 20 preguntas, núcleo determinista, grafo LangGraph, proveedor LLM con mock/Gemini, interfaz Flet y suite de pruebas).
- **Fase 8 completada:** integración real con Gemini (requiere `GEMINI_API_KEY`, provider `mock|gemini`).
- **Fase Docker completada:** monolito `python:3.14-slim` + `docker-compose.yml` + CI GHCR (`.github/workflows/docker.yml`).
- Suite de tests: **65 tests** (`pytest`, `tests/test_app.py` incluido; 142 preguntas totales).

## Stack

- Python 3.14 + venv en Windows (`PowerShell`) — Docker base `python:3.14-slim-bookworm` (ver `Dockerfile:1`).
- `langgraph` (grafo + interrupt/checkpointer), `pydantic` (dominios), `google-genai` (Gemini), `flet` (UI), `pytest` (tests).
- Docker + Compose + GHCR (CI).

## Estructura

```
Dockerfile              Monolito Flet (python:3.14-slim, puerto 8000)
docker-compose.yml      Orquesta flet + tests (profile)
archive/app_streamlit.py Interfaz Streamlit deprecada (Fase 6, solo referencia)
flet_app/               Interfaz Flet (Fase 6A) — main.py, router, views, state, theme
src/
  config.py             Carga de .env (pydantic-settings)
  graph.py              Grafo LangGraph de la sesión
  models/               Dominios Pydantic (Section, Question, SessionState, ...)
  core/                 Lógica determinista (evaluación + fallback de feedback)
  data/                 Banco de preguntas e imágenes
  providers/            Capa de proveedores de feedback (ABC, mock, Gemini)
data/
  questions.json        Banco de preguntas (142 totales; RQ 54 tras ampliación RQ-030..054)
  images/               Imágenes de preguntas (RQ-002.png, RQ-003.png, RQ-033.png...)
tests/                  Suite de pruebas (pytest)
docs/                   Documentación del proyecto
```

## Configuración

1. Crear el entorno virtual e instalar dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Crear `.env` a partir de `.env.example` (o `.env` ya existente):

```
GEMINI_API_KEY=          # Clave para el proveedor Gemini (opcional)
FEEDBACK_PROVIDER=mock   # mock | gemini
GEMINI_MODEL=gemini-3.5-flash
```

## Uso

### Local sin Docker (Flet)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\flet.exe run --web flet_app/main.py   # http://localhost:8550
# o desktop:
.\.venv\Scripts\python.exe flet_app/main.py
```

### Con Docker (recomendado — paridad prod/CI)

```powershell
docker compose up --build              # http://localhost:8000
docker compose --profile tests run --rm tests
docker compose down
```

**Ejecutar la suite de pruebas (sin Docker):**

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q        # 65 tests
```

**Habilitar Gemini real:** poner `GEMINI_API_KEY` y `FEEDBACK_PROVIDER=gemini` en `.env`. Ver `docs/RUNBOOK.md`.

## Documentación

- `docs/ARCHITECTURE.md` — arquitectura real del sistema y flujo end-to-end.
- `docs/DATA_MODEL.md` — modelos Pydantic y esquema del banco de preguntas.
- `docs/RUNBOOK.md` — guía de ejecución, configuración y solución de problemas.
- `docs/EVOLUTION.md` — roadmap de evolutivos propuestos.
- `docs/specs/01_specification.md` — especificación funcional (fuente de verdad de comportamiento).
- `docs/planning/` — planes de ejecución históricos (`PROJECT_PLAN.md`, `PLAN_IMAGENES.md`).