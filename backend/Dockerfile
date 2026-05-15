# Backend RCA — FastAPI + uvicorn
# Build: docker build -t rca-backend ./backend
# Run:   docker run -p 8010:8010 --env-file ./backend/.env rca-backend

FROM python:3.11-slim AS base

# Evita .pyc, output sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Deps de SO mínimas (libpq para psycopg cuando se use PG)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer de dependencias separado para cache
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Código
COPY backend/ /app/

# Usuario no-root
RUN useradd -m -u 1000 rca && chown -R rca:rca /app
USER rca

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8010/health || exit 1

# Aplicar migraciones y arrancar — todo con SIGTERM-aware
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8010}"]
