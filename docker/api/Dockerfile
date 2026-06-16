# ─────────────────────────────────────────────────────────────
# Finance API — Multi-stage Docker Build
# Usa pip diretamente (sem Poetry) para builds previsíveis
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─────────────────────────────────────────────────────────────
# Dependencies stage — instalado em camada separada para cache
# ─────────────────────────────────────────────────────────────
FROM base AS deps

COPY docker/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────
# Runtime stage — imagem final da API
# ─────────────────────────────────────────────────────────────
FROM base AS runtime

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY app/ ./app/
COPY ml/ ./ml/

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-"]

# ─────────────────────────────────────────────────────────────
# Streamlit stage — dashboard executivo
# ─────────────────────────────────────────────────────────────
FROM runtime AS streamlit

COPY dashboards/ ./dashboards/

EXPOSE 8501

CMD ["streamlit", "run", "dashboards/streamlit/app.py", \
     "--server.port", "8501", "--server.headless", "true", \
     "--server.address", "0.0.0.0"]
