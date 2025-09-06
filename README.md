# Smart Graphic Designer API

End-to-end FastAPI service implementing the AGENTS.md spec: `/render`, `/ingest`, `/canon/derive`, `/critique`, `/healthz`, `/metrics`, with Guardrails-style JSON Schema validation, Redis cache, Qdrant vector store, Cloudflare R2 storage, Kong gateway config, and Langfuse tracing hooks.

Quick start
- Copy `.env.example` to `.env` and set required keys (OpenRouter, R2, etc.).
- Run `docker compose up -d redis qdrant postgres langfuse kong`.
- `cd api && poetry install && poetry run uvicorn app.main:app --reload`.
- Try requests in `examples/curl.http`.
- Optional local storage: `docker compose up -d minio` then set in `.env`:
  - `S3_ENDPOINT_URL=http://localhost:9000`
  - `R2_ACCESS_KEY_ID=minioadmin`, `R2_SECRET_ACCESS_KEY=minioadmin`, `R2_BUCKET=assets`
  - Create bucket once: open MinIO console http://localhost:9001 and add bucket `assets`.

Notes
- `/render` calls OpenRouter Gemini 2.5 Flash Image and stores outputs in S3-compatible storage (R2 in prod; MinIO locally).
- Guardrails JSON schemas live in `guardrails/` and are enforced on plan/canon/critique.
- OpenAPI is in `api/openapi.yaml`.

## Frontend (apps/web)

- Dev: `pnpm -C apps/web dev`
- Build: `pnpm -C apps/web build`
- E2E: `pnpm -C apps/web test:e2e`

### Env

Create `apps/web/.env.local`:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_POSTHOG_KEY=phc_...
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
CLERK_PUBLISHABLE_KEY=...
```

### Feature Flags

Flags default in `FlagsProvider`:
- preview_mode_v2
- enable_templates
- enable_collaboration

### Ship Gate

- Lighthouse mobile ≥ 90, CLS ≤ 0.1, LCP ≤ 2.5s
- Initial JS ≤ 200KB (size guard)
- E2E smoke green; no new critical issues
- Visual diffs approved
