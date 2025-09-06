FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry and psycopg2
RUN pip install poetry psycopg2-binary

# Copy only pyproject.toml and poetry.lock to leverage Docker cache
COPY api/pyproject.toml api/poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction --no-ansi --no-root

# Copy the API code
COPY api/ .

# Copy policies directory
COPY policies ./policies

# Copy guardrails directory
COPY guardrails ./guardrails

# Copy migrations
COPY infra/migrations ./infra/migrations

# Create required directories
RUN mkdir -p var/storage

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
