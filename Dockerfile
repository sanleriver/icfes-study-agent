# syntax=docker/dockerfile:1.6
ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM deps AS runtime
# Copiar codigo y datos (monolito: src + flet_app + data)
COPY src/ ./src/
COPY flet_app/ ./flet_app/
COPY data/ ./data/
COPY tests/ ./tests/
# flet_app assets deben estar incluidos (ya dentro de flet_app)
# Crear usuario no-root
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser
# Flet web corre en 8000 por defecto; exponer
EXPOSE 8000
# Healthcheck: Flet web responde HTML
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD wget -qO- http://127.0.0.1:8000/ > /dev/null || exit 1
# Variables por defecto (pueden sobreescribirse via env_file)
ENV FEEDBACK_PROVIDER=mock \
    GEMINI_MODEL=gemini-3.5-flash
# Comando por defecto: Flet web en 0.0.0.0:8000
CMD ["flet", "run", "--web", "--host", "0.0.0.0", "--port", "8000", "flet_app/main.py"]
