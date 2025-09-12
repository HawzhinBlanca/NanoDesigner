# Smart Graphic Designer - Developer Makefile

.PHONY: help up down logs api web test fe-test e2e-smoke lhci-smoke

help:
	@echo "Targets:"
	@echo "  up           - start core infra via docker compose"
	@echo "  down         - stop all docker compose services"
	@echo "  logs         - tail docker logs"
	@echo "  api          - run FastAPI locally (reload)"
	@echo "  web          - run Next.js dev server"
	@echo "  test         - run API unit tests (no externals)"
	@echo "  fe-test      - run frontend unit tests"
	@echo "  e2e-smoke    - quick curl smoke against API endpoints"
	@echo "  lhci-smoke   - run Lighthouse CI (requires running web)"

up:
	docker compose up -d redis qdrant postgres langfuse kong minio

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

api:
	cd api && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	pnpm -C apps/web dev

test:
	cd api && poetry run pytest -q -k "not requires OpenRouter"

fe-test:
	VITEST_POOL=forks pnpm -C apps/web test -- --run --pool=forks

e2e-smoke:
	@echo "Checking API health..."
	@curl -fsS http://localhost:8000/healthz | jq . >/dev/null && echo "✅ /healthz OK" || (echo "❌ /healthz failed" && exit 1)
	@echo "Posting /render dry-run (no externals, expects validation error)..."
	@curl -sS -X POST http://localhost:8000/render \
	  -H 'Content-Type: application/json' \
	  -d '{"project_id":"smoke","prompts":{"task":"create","instruction":"Create a banner"},"outputs":{"count":1,"format":"png","dimensions":"256x256"}}' \
	  | jq '.status? // .assets? // .error? // .audit?'
	@echo "✅ Smoke completed"

lhci-smoke:
	pnpm -C apps/web lhci:run
