#!/usr/bin/env bash
set -euo pipefail
echo "[perf] Run basic load test with autocannon (node) or bombardier (go)"
echo "Example: bombardier -c 10 -n 200 -m POST -H 'Content-Type: application/json' -b '{\n  \"project_id\":\"demo\",\n  \"prompts\":{\"task\":\"create\",\"instruction\":\"Create a banner\"},\n  \"outputs\":{\"count\":1,\"format\":\"png\",\"dimensions\":\"512x512\"}\n}' http://localhost:8000/render"
