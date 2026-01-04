FROM python:3.11-slim

ARG POETRY_VERSION=1.8.3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==${POETRY_VERSION}"

# dependency layer
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

# code layer
COPY . .

# default command runs the CLI agent
CMD ["python", "main.py"]


