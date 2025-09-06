#!/usr/bin/env bash
set -euo pipefail
BASE_URL=${1:-http://localhost:8000}
echo "[seed] Ingest demo assets"
curl -sSf -X POST "$BASE_URL/ingest" -H 'Content-Type: application/json' -d '{
  "project_id": "demo",
  "assets": ["https://example.com/brand.pdf", "https://example.com/logo.png"]
}' | jq .
