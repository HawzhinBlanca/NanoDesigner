#!/usr/bin/env bash
set -euo pipefail

echo "[dev] Starting dependencies with Docker Compose (redis, qdrant, postgres, langfuse)"
docker compose up -d redis qdrant postgres langfuse || true

echo "[dev] Tip: Kong is available via 'docker compose up -d kong' on http://localhost:8080"

echo "[dev] Installing API dependencies via Poetry"
cd api
if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry not found; please install poetry first: https://python-poetry.org/docs/#installation"
  exit 1
fi
poetry install

echo "[dev] Running API server at :8000"
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
