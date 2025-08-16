# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app

# системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# poetry
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# зависимости бэкенда (важно: копируем именно backend/pyproject.toml)
COPY backend/pyproject.toml backend/poetry.lock* ./backend/
RUN cd backend && poetry install --only main --no-root

# код
COPY backend ./backend
COPY analytics ./analytics

EXPOSE 8080

# запустим API как пакет backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
