#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${1:-http://localhost:8000}
echo "[smoke] Health"
curl -sSf "$BASE_URL/healthz" | jq .

echo "[smoke] Render sample"
curl -sSf -X POST "$BASE_URL/render" \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id":"demo",
    "prompts":{"task":"create","instruction":"Create a banner"},
    "outputs":{"count":1,"format":"png","dimensions":"512x512"}
  }' | jq .
