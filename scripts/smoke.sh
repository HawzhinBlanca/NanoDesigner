#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}
WEB_BASE=${WEB_BASE:-http://localhost:3000}

echo "🔎 API: $API_BASE, Web: $WEB_BASE"

echo "→ Checking API /healthz"
curl -fsS "$API_BASE/healthz" | jq . >/dev/null && echo "✅ API healthy" || { echo "❌ API health failed"; exit 1; }

echo "→ Checking API /metrics"
curl -fsS "$API_BASE/metrics" | jq . >/dev/null && echo "✅ API metrics" || echo "⚠️ metrics not JSON (ok if basic)"

echo "→ Rendering (may fail gracefully without externals)"
curl -sS -X POST "$API_BASE/render" \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"smoke","prompts":{"task":"create","instruction":"Create a banner"},"outputs":{"count":1,"format":"png","dimensions":"256x256"}}' \
  | jq '.assets? // .error? // .audit?'

echo "→ Checking Web home"
curl -fsS "$WEB_BASE" >/dev/null && echo "✅ Web reachable" || echo "⚠️ Web not running"

echo "✅ Smoke complete"
