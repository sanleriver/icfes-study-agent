# Plan de Dockerización — Tutor ICFES Saber Pro (Monolito Flet)

> **Ubicación:** `docs/planning/docker/PLAN_DOCKER.md`  
> **Fecha:** 2026-08-23  
> **Estado:** Plan aprobado — pendiente de implementación  
> **Decisiones clave:** Deprecar `app.py` (Streamlit), base `python:3.14-slim-bookworm`, `requirements.txt` monolito único, arquitectura monolito single-image.

---

## 1. Objetivo

Crear estructura Docker reproducible para el proyecto `icfes_agent_ecosystem` (back en `src/` + front en `flet_app/`) que permita:

1. `docker build` en cualquier entorno (local Windows/Linux, CI Ubuntu).
2. `docker compose up --build` levanta la app en local con 1 comando (hot-reload en dev).
3. CI en GitHub Actions: `test` + `build` + `push` a `ghcr.io` + smoke test en PR.
4. Gestión de secretos sin commitear `.env` (`FEEDBACK_PROVIDER=mock` por defecto en CI).
5. Imagen pequeña, non-root, healthcheck, layer caching.

---

## 2. Diagnóstico del estado actual

### 2.1 Estructura verificada

| Capa | Ruta | Rol |
| :--- | :--- | :--- |
| Core/Back | `src/graph.py:84` `build_graph`, `src/models/session.py` (`operator.add` reducer), `src/providers/` (`create_feedback_provider`), `src/config.py:7` (`PROJECT_ROOT/.env`) | Lógica determinista + LangGraph + LLM provider |
| Datos | `data/questions.json`, `data/images/` (`src/data/images.py:IMAGES_DIR`) | Banco 20 preguntas + imágenes |
| Front Flet | `flet_app/main.py:28` `ft.run(main)`, `flet_app/router.py:42` `setup_router`, `flet_app/state/graph_runner.py:18` `GraphRunner` (`asyncio.to_thread`), `flet_app/state/session_manager.py:13` `page.session.store`, `flet_app/theme.py:15` | UI única (post-deprecación) |
| Legado a deprecar | `app.py:157` Streamlit, `requirements.txt:6` `streamlit>=1.30.0` | Se elimina |
| Config | `.env` (`.env.example` plantilla), `requirements.txt:1` monolito 9 deps, `flet_app/build/.python-version:1` `3.14`, `.venv` Python 3.14.6 | Entorno |
| CI roto | `.github/workflows/docker.yml:15` referencia `docker/Dockerfile` y `docker-compose.yml` inexistentes (`glob **/Dockerfile*` → 0) | Fix requerido |

### 2.2 Hallazgo arquitectónico

`flet_app` **no es backend HTTP independiente** — importa `src` in-process (`from src.graph import build_graph` en `flet_app/state/graph_runner.py:11`). No hay FastAPI. "Back en raíz" es librería. Dockerizar como 2 microservicios no aporta valor ahora. **Monolito single-image es lo correcto** (future API → split después).

### 2.3 Validación Python base (Context7 MCP)

| Librería | Context7 ID | `requires-python` | Fuente |
| :--- | :--- | :--- | :--- |
| Flet | `/flet-dev/flet` | `>=3.10`, soporta `3.12, 3.13, 3.14` (default `3.14`) | `website/docs/getting-started/installation.md`, `.../publish/index.md`, `.../default-bundled-python-3-14.md` |
| LangGraph | `/langchain-ai/langgraph` | `>=3.10` (`libs/langgraph/pyproject.toml`) | Context7 query-docs |
| Pydantic | `/pydantic/pydantic` | `>=3.9`, contribuye `3.10-3.14` (`docs/contributing.md`) | Context7 + `docs/install.md` |
| google-genai | — (PyPI metadata) | `>=3.10` (`2.18.1` instalada) | `importlib.metadata` local |
| Pydantic-settings | `/pydantic/pydantic-settings` | `>=3.10` | local `2.15.0` |

Verificación local: `Python 3.14.6` + `flet 0.86.5` + `langgraph 1.2.11` + `pydantic 2.13.4` + `google-genai 2.18.1` → todos OK en 3.14, `flet_app/build/.python-version` ya fija `3.14`.

**Decisión:** `ARG PYTHON_VERSION=3.14` → `python:3.14-slim-bookworm`. Fallback documentado `3.12-slim-bookworm` si algún wheel C/Rust futuro no tiene wheel para 3.14 (cambiar 1 ARG).

---

## 3. Decisiones de diseño

### 3.1 Deprecación `app.py`

- Eliminar `app.py` del build (mover a `archive/app_streamlit.py` o borrar).
- Eliminar `streamlit>=1.30.0` de `requirements.txt:6` (ahorro ~300 MB).
- Eliminar `EXPOSE 8501` y servicio `streamlit` de compose.
- Actualizar docs: `README.md:20`, `docs/ARCHITECTURE.md:10`, `docs/RUNBOOK.md:31`.

### 3.2 Requirements — Monolito único

**Mantener 1 `requirements.txt`** (no split). Razones:
- Back y front son mismo proceso → mismas deps (`pydantic`, `langgraph`, `google-genai`, `flet`). Split duplicaría y rompería cache.
- `requirements.txt` 9 líneas, sin conflictos.
- Docker layer caching óptimo: 1 `COPY requirements.txt` + 1 `RUN pip install`.
- `tests/conftest.py:9` fuerza `mock` → no necesita deps extra.

**Mejora incluida:** pinnear versiones exactas (`==`) en lugar de `>=` para reproducibilidad CI. Ej. `flet==0.86.5`, `langgraph==1.2.11`, `google-genai==2.18.1`, `pydantic==2.13.4`. Generar con `pip freeze` o `pip-compile`.

### 3.3 Arquitectura Docker

**Single-image multi-stage:**

```
base (python:3.14-slim-bookworm + wget)
  → deps (pip install -r requirements.txt)
    → runtime (COPY src/ flet_app/ data/, USER appuser, EXPOSE 8000, HEALTHCHECK, CMD flet web)
```

No multi-target streamlit. `docker-compose.yml` con `flet` + `tests` (profile). `docker-compose.override.yml` para dev con bind-mounts.

---

## 4. Estructura de archivos a crear/modificar

```
/
├── Dockerfile                          # NEW — multi-stage, ARG 3.14, non-root, 8000, healthcheck
├── docker-compose.yml                  # NEW — service flet (8000:8000), tests (profile)
├── docker-compose.override.yml         # NEW — dev override con volumes hot-reload
├── .dockerignore                       # NEW — .venv, __pycache__, .git, .env, .pytest_cache, flet_app/.flet/storage, flet_app/build
├── requirements.txt                    # MOD — quitar streamlit, pinnear ==
├── .github/workflows/docker.yml        # FIX — file: ./Dockerfile, paths, job test + build
├── archive/app_streamlit.py            # MOV — app.py deprecado (o borrar)
├── README.md                           # MOD — sección Docker, quitar streamlit run
├── docs/ARCHITECTURE.md                # MOD — diagrama sin Streamlit, añadir contenedor
├── docs/RUNBOOK.md                     # MOD — instrucciones docker compose
└── docs/planning/docker/PLAN_DOCKER.md # THIS FILE
```

Actualizar `.gitignore:7` para incluir `docker-compose.override.yml` si se desea ignorar local.

---

## 5. Detalle Dockerfile

```dockerfile
ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends wget curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM deps AS runtime
COPY src/ ./src/
COPY flet_app/ ./flet_app/
COPY data/ ./data/
# No copiar .env — se inyecta vía env_file/compose
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD wget -qO- http://127.0.0.1:8000/ || exit 1
CMD ["python", "-m", "flet", "run", "flet_app/main.py", "--web", "--host", "0.0.0.0", "--port", "8000"]
```

**Notas:**
- `flet_app/assets/images/` y `data/images/` ambos copiados (ver `flet_app/views/question_view.py:23` `_ASSETS_IMAGES_DIR` y `src/data/images.py:IMAGES_DIR`).
- `PYTHONPATH=/app` implícito por `WORKDIR`; `tests/conftest.py:5` sigue funcionando.
- Si `flet run` no bindea headless, alternativa: `CMD ["python", "flet_app/main.py"]` y ajustar `flet_app/main.py:30` a `ft.run(main, view=ft.WEB_BROWSER, port=8000, host="0.0.0.0")`.
- `wget` vs `curl`: base slim ya trae `wget`; `curl` se instala extra si se prefiere.

---

## 6. Detalle docker-compose.yml

```yaml
services:
  flet:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - FEEDBACK_PROVIDER=${FEEDBACK_PROVIDER:-mock}
      - GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.5-flash}
      # GEMINI_API_KEY viene de .env o secrets
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:8000/"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  tests:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["pytest", "-q"]
    env_file:
      - .env
    environment:
      - FEEDBACK_PROVIDER=mock
    profiles: ["tests"]
```

**docker-compose.override.yml** (solo dev, opcional gitignore):

```yaml
services:
  flet:
    volumes:
      - ./src:/app/src
      - ./flet_app:/app/flet_app
      - ./data:/app/data
    environment:
      - FEEDBACK_PROVIDER=mock
```

**Uso local (PowerShell):**

```powershell
docker compose up --build              # prod-like, http://localhost:8000
docker compose --profile tests run --rm tests
docker compose down

# Dev con hot-reload (usa override automáticamente si existe)
docker compose up --build --watch  # si compose watch habilitado
```

---

## 7. .dockerignore

```
.venv/
venv/
__pycache__/
*.py[cod]
*.pyc
.git/
.gitignore
.env
.streamlit/
.pytest_cache/
.mypy_cache/
data/*.tmp
flet_app/.flet/storage/
flet_app/build/
Thumbs.db
.DS_Store
docs/
tests/
.github/
```

---

## 8. requirements.txt (propuesto, pinneado)

```
langgraph==1.2.11
langchain==0.3.26
pydantic==2.13.4
pydantic-settings==2.15.0
python-dotenv==1.1.1
flet==0.86.5
google-genai==2.18.1
pytest==8.4.1
# streamlit eliminado (deprecado app.py)
```

*Generar exactas con `.\.venv\Scripts\python.exe -m pip freeze` y filtrar.*

---

## 9. CI/CD GitHub Actions — Fix `.github/workflows/docker.yml`

**Problemas actuales a corregir:**
- `file: docker/Dockerfile` → `file: ./Dockerfile` (raíz)
- `paths` incluye `docker/**` inexistente → cambiar a `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Falta job `test` (actual solo `build`)
- `IMAGE_NAME` con sufijo `-flet` innecesario tras deprecación

**Pipeline propuesto:**

```yaml
name: docker

on:
  push:
    branches: [main, master]
    paths: [flet_app/**, src/**, data/**, requirements.txt, Dockerfile, docker-compose.yml, .dockerignore, .github/workflows/docker.yml]
  pull_request:
    paths: [flet_app/**, src/**, data/**, requirements.txt, Dockerfile, docker-compose.yml]
  workflow_dispatch:

permissions: { contents: read, packages: write }
env: { REGISTRY: ghcr.io, IMAGE_NAME: ${{ github.repository }} }

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14" }
      - run: pip install -r requirements.txt
      - run: pytest -q

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with: { registry: ${{ env.REGISTRY }}, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          platforms: linux/amd64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - if: github.event_name == 'pull_request'
        run: |
          docker build -f Dockerfile -t tutor-icfes:test .
          docker run --rm -d -p 8000:8000 --name tutor-test tutor-icfes:test
          for i in 1 2 3 4 5 6; do
            if wget -qO- http://127.0.0.1:8000/ | grep -q "Tutor"; then echo "smoke ok"; break; fi
            sleep 5
          done
          wget -qO- http://127.0.0.1:8000/ | head -n 20
          docker rm -f tutor-test
```

- Secrets: `GEMINI_API_KEY` via `secrets.GEMINI_API_KEY` solo si `FEEDBACK_PROVIDER=gemini` en smoke; en CI usar `mock`.
- Triggers `paths` evitan builds innecesarios.

---

## 10. Variables de entorno

| Variable | Default | Fuente |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | "" | `.env` local / GitHub Secrets |
| `FEEDBACK_PROVIDER` | `mock` | `.env` / compose `environment` |
| `GEMINI_MODEL` | `gemini-3.5-flash` | `.env` / compose |

`src/config.py:9` lee `PROJECT_ROOT/.env` — dentro del contenedor `PROJECT_ROOT=/app`, funciona si `.env` montado vía `env_file`; si no, usa env vars del contenedor (pydantic-settings `extra="ignore"`). En CI `FEEDBACK_PROVIDER=mock` evita `ValueError` sin `GEMINI_API_KEY` (`src/config.py:20`).

`.env.example` ampliar con:

```
FLET_PORT=8000
# GEMINI_API_KEY= deja vacío para mock
```

---

## 11. Documentación a actualizar

- `README.md:52` — reemplazar `streamlit run app.py` por `docker compose up --build` + `flet run`.
- `docs/ARCHITECTURE.md:10` — diagrama sin Streamlit, añadir bloque Docker (`Flet web:8000` → `GraphRunner` → `InMemorySaver`).
- `docs/RUNBOOK.md:31` — nueva sección "Ejecución con Docker" (local + CI).
- `docs/specs/01_specification.md` — reflejar deprecación Streamlit si se menciona.

---

## 12. Orden de implementación

| Fase | Artefacto | Esfuerzo |
| :--- | :--- | :--- |
| 1 | `.dockerignore` + `Dockerfile` (ARG 3.14, multi-stage) | 30 min |
| 2 | `docker-compose.yml` + `docker-compose.override.yml` | 20 min |
| 3 | `requirements.txt` (quitar streamlit, pinnear ==) | 10 min |
| 4 | Fix `flet_app/main.py:30` para web headless si `flet run` falla | 15 min |
| 5 | Reescribir `.github/workflows/docker.yml` | 30 min |
| 6 | Deprecar `app.py` → `archive/` + actualizar docs | 20 min |
| 7 | Verificación: `docker build`, `docker compose up`, `pytest` host vs container, smoke CI | 30 min |

**Total estimado:** 2.5–3 horas.

---

## 13. Verificación

- **Local Windows:** `docker build -t tutor:test .` + `docker run -d -p 8000:8000 tutor:test` + `wget http://localhost:8000` contiene "Tutor ICFES".
- **Compose:** `docker compose up --build` + navegar `http://localhost:8000` → config → pregunta → results.
- **Tests:** `.\.venv\Scripts\python.exe -m pytest tests -q` (64 tests) vs `docker compose --profile tests run --rm tests` (mismo resultado).
- **CI:** push a branch → job `test` verde, job `build` cache `type=gha`, smoke PR pasa, push a `main` publica `ghcr.io/OWNER/tutor-icfes:latest`.

---

## 14. Riesgos y mitigaciones

| Riesgo | Mitigación |
| :--- | :--- |
| `flet run --web` no bindea `0.0.0.0` en slim | Ajustar `flet_app/main.py:30` con `view=ft.WEB_BROWSER` + `host` param |
| Wheels faltantes para 3.14 (futura dep) | Cambiar `ARG PYTHON_VERSION=3.12` y rebuild |
| `GEMINI_API_KEY` filtrada en imagen | No `COPY .env`, solo `env_file` runtime |
| `data/images` no resueltas | Copiar ambas rutas (`data/images` + `flet_app/assets/images`) y validar `validate_image_references()` |

---

## 15. Próximos pasos (requiere tu GO)

1. Confirmar pinneo exacto `requirements.txt` (¿`pip freeze` autogenerado o mantener `>=`?).
2. Ejecutar Fases 1–7 en orden.
3. Decidir si `app.py` se borra o se archiva en `archive/`.

> Plan listo para implementación. Siguiente comando sugerido: `docker build` + `docker compose up` tras Fase 1–2.

