{
  "doc": "CLAUDE.md",
  "version": "1.0.0",
  "updated": "2025-09-05",
  "purpose": "Authoritative, end-to-end implementation plan for the Smart Graphic Designer backend using FastAPI → OpenRouter (direct), Gemini 2.5 Flash Image for images, Google Document AI for OCR/structure, Qdrant+Redis for memory, R2+Cloudflare for assets, Kong+Clerk for auth/gateway, Langfuse for traces, Guardrails AI for validation. This JSON is optimized for Anthropic Claude Code agent execution: explicit tasks, file map, schemas, policies, tests, and acceptance criteria. Zero placeholders; fail on TODOs.",
  "goals": [
    "Ship /render first (Gemini 2.5 Flash Image via OpenRouter) with SynthID verification logs",
    "Implement Redis caching for embeddings + request dedupe",
    "Enforce Kong rate limits/JWT auth (Clerk) before public traffic",
    "Guardrails AI schemas on all critical outputs (render plans, brand canon, critique)",
    "Observability with Langfuse on every LLM call (traces, cost, prompts)"
  ],
  "constraints": [
    "No Dify in the runtime path (optional internal ops UI only)",
    "All LLM & image generation via OpenRouter HTTP API (direct)",
    "Dev uses local disk for asset storage; Prod uses S3-compatible (e.g., Cloudflare R2) with CDN",
    "Embeddings local-only (no OpenRouter embeddings); cache hits via Redis",
    "Keep infra lean: Docker Compose for dev; K8s manifests provided but optional"
  ],
  "system_overview": {
    "flow": [
      "Client → Kong (JWT/RateLimit) → FastAPI",
      "FastAPI reads Brand Canon from Qdrant/Postgres; caches in Redis",
      "FastAPI calls OpenRouter for: planning (GPT-class), critique (Claude), quick drafts (DeepSeek), image gen (Gemini 2.5 Flash Image)",
      "Assets stored in local disk (dev) or S3-compatible object store (prod); public via /static in dev or CDN signed URLs in prod",
      "Document ingest via Unstructured → Google Document AI → Canon normalizer",
      "Guardrails validates structured outputs; Langfuse traces all model calls"
    ],
    "modules": [
      "api_service",
      "openrouter_policy",
      "image_pipeline",
      "ingest_pipeline",
      "memory_store",
      "cache",
      "gateway_auth",
      "storage_cdn",
      "observability",
      "evaluation",
      "security"
    ]
  },
  "repository_layout": {
    "root": [
      "README.md",
      "CLAUDE.md.json",
      ".env.example",
      "docker-compose.yml",
      "Makefile",
      "infra/kong/kong.yaml",
      "infra/k8s/*.yaml",
      "infra/migrations/*.sql",
      "api/pyproject.toml",
      "api/app/main.py",
      "api/app/routers/{render,ingest,canon,critique,health}.py",
      "api/app/services/{openrouter,gemini_image,docai,unstructured,canon,embed,qdrant,redis,guardrails,langfuse}.py",
      "api/app/models/{schemas.py,errors.py}",
      "api/app/core/{config.py,security.py,rate_limits.py,logging.py}",
      "api/app/tests/{integration,load,contracts}/*.py",
      "api/openapi.yaml",
      "guardrails/{render_plan.json,canon.json,critique.json}",
      "policies/openrouter_policy.json",
      "scripts/{dev_bootstrap.sh,seed_demo.sh,smoke.sh,perf.sh,db_migrate.sh}",
      "examples/{curl,postman}.http"
    ]
  },
  "environment": {
    "env_vars": {
      "OPENROUTER_API_KEY": "string",
      "LANGFUSE_PUBLIC_KEY": "string",
      "LANGFUSE_SECRET_KEY": "string",
      "LANGFUSE_HOST": "https://cloud.langfuse.com",
      "REDIS_URL": "redis://redis:6379/0",
      "QDRANT_URL": "http://qdrant:6333",
      "QDRANT_API_KEY": "",
      "STORAGE_BACKEND": "auto(dev=local,prod=s3) | local | s3",
      "LOCAL_STORAGE_DIR": "var/storage",
      "SERVICE_BASE_URL": "http://localhost:8000",
      "S3_ENDPOINT_URL": "https://<provider-endpoint> (optional; e.g., R2/Spaces/MinIO)",
      "R2_ACCOUNT_ID": "string (optional)",
      "R2_ACCESS_KEY_ID": "string (optional)",
      "R2_SECRET_ACCESS_KEY": "string (optional)",
      "R2_BUCKET": "assets (optional)",
      "CLOUDFLARE_ACCOUNT_ID": "string",
      "CLOUDFLARE_WORKER_SIGNER_SECRET": "string",
      "GOOGLE_APPLICATION_CREDENTIALS": "/secrets/gcp.json",
      "DOC_AI_PROCESSOR_ID": "projects/…/locations/…/processors/…",
      "CLERK_JWKS_URL": "https://clerk.your-domain/.well-known/jwks.json",
      "KONG_ADMIN_URL": "http://kong:8001",
      "SERVICE_NAME": "sgd-api",
      "SERVICE_ENV": "dev",
      "SERVICE_REGION": "eu-central",
      "LOG_LEVEL": "INFO"
    }
  },
  "components": {
    "api_service": {
      "framework": "FastAPI",
      "endpoints": [
        {
          "method": "POST",
          "path": "/render",
          "auth": "JWT (Clerk) via Kong; service-to-service HMAC optional",
          "rate_limit": "100 req/min per API key",
          "request_schema_ref": "#/schemas/RenderRequest",
          "response_schema_ref": "#/schemas/RenderResponse",
          "guardrails_contract": "guardrails/render_plan.json",
          "flow": [
            "Validate request against JSON Schema",
            "Fetch/derive Brand Canon (Qdrant/Postgres)",
            "Compile render plan (OpenRouter → planner_model)",
            "Guardrails validate plan → reject if invalid",
            "Call image generator (OpenRouter → gemini-2.5-flash-image)",
            "Store result in R2; write metadata (Postgres)",
            "Run SynthID verify (log stamp if API provides; else metadata note)",
            "Critique step (OpenRouter → critic_model) vs Canon → optional auto-repair",
            "Return signed CDN URL + audit"
          ]
        },
        {
          "method": "POST",
          "path": "/ingest",
          "request_schema_ref": "#/schemas/IngestRequest",
          "response_schema_ref": "#/schemas/IngestResponse",
          "flow": [
            "Upload to R2 (quarantine path)",
            "Unstructured → basic parse",
            "Document AI → structure (tables/forms/layout)",
            "Canon extractor (LLM) → normalized JSON",
            "Embed & upsert to Qdrant; cache in Redis",
            "Return stats + IDs"
          ]
        },
        {
          "method": "POST",
          "path": "/canon/derive",
          "request_schema_ref": "#/schemas/CanonDeriveRequest",
          "response_schema_ref": "#/schemas/CanonDeriveResponse",
          "guardrails_contract": "guardrails/canon.json"
        },
        {
          "method": "POST",
          "path": "/critique",
          "request_schema_ref": "#/schemas/CritiqueRequest",
          "response_schema_ref": "#/schemas/CritiqueResponse",
          "guardrails_contract": "guardrails/critique.json"
        },
        { "method": "GET", "path": "/healthz" },
        { "method": "GET", "path": "/metrics" }
      ]
    },
    "openrouter_policy": {
      "file": "policies/openrouter_policy.json",
      "description": "Task→model routing, budget caps, fallbacks, prompt templates, retry/backoff",
      "spec": {
        "tasks": {
          "planner": { "primary": "openrouter/gpt-5", "fallbacks": ["openrouter/claude-4.1"], "max_cost_usd": 0.02 },
          "critic": { "primary": "openrouter/claude-4.1", "fallbacks": ["openrouter/gpt-5"], "max_cost_usd": 0.02 },
          "draft":  { "primary": "openrouter/deepseek-v3.1", "fallbacks": ["openrouter/gpt-5-mini"], "max_cost_usd": 0.005 },
          "image":  { "primary": "openrouter/gemini-2.5-flash-image", "max_cost_usd": 0.10 }
        },
        "retry": { "max_attempts": 2, "backoff_ms": 400 },
        "timeouts_ms": { "default": 20000, "image": 45000 },
        "telemetry": { "langfuse_trace": true }
      }
    },
    "image_pipeline": {
      "generator": "Gemini 2.5 Flash Image via OpenRouter",
      "inputs": ["multi-image refs", "brand canon constraints", "edit ops"],
      "outputs": ["object store key (local or S3)", "SynthID metadata"],
      "post": ["critic review", "auto-repair (optional)"],
      "safety": ["max dimensions 4096x4096", "max area 16777216 px", "NSFW/off-brand filters"]
    },
    "ingest_pipeline": {
      "steps": [
        "Upload asset → R2 quarantine/",
        "AV scan (ClamAV) → block on detection; log threat signature",
        "MIME allowlist verification (libmagic) → reject mismatched types",
        "EXIF metadata strip for images (privacy) before promotion",
        "Unstructured (text/html/pdf/office) → clean text blocks",
        "Google Document AI (processor_id) → layout/fields/tables",
        "LLM Canon Extractor → normalized brand JSON",
        "Embed local (bge-m3) → upsert Qdrant (collection: brand_assets)",
        "Cache key facts in Redis (e.g., palette hexes, font family, logo-safe-zones)"
      ]
    },
    "memory_store": {
      "vector_db": "Qdrant",
      "collections": ["brand_assets", "design_examples", "style_guides"],
      "rdbms": "Postgres (metadata, jobs, audits)",
      "schemas": ["see #/schemas/*"]
    },
    "cache": {
      "redis": {
        "namespaces": {
          "embed_cache": "sha256(content) → vector",
          "plan_cache": "sha256(canon+prompt) → plan",
          "rate_counters": "per-key sliding window"
        },
        "ttl_seconds": { "embed_cache": 864000, "plan_cache": 86400 }
      }
    },
    "org_isolation": {
      "qdrant": "Per-org collections (e.g., brand_assets_{org_id})",
      "r2": "Per-org prefixes (e.g., org/{org_id}/quarantine|public/)",
      "postgres": "Row Level Security (RLS) on org_id across metadata/audit tables"
    },
    "cost_control": {
      "gateway_budget_plugin": "Kong plugin enforces per-org daily caps; 429 with Retry-After on exceed",
      "server_tracking": "Accrue usage per request; emit 50/80/100% alerts via webhook/Slack",
      "policy": {
        "daily_budget_usd": "env-configurable",
        "alert_thresholds": [0.5, 0.8, 1.0]
      }
    },
    "gateway_auth": {
      "kong": {
        "declarative_config": "infra/kong/kong.yaml",
        "plugins": [
          "jwt (Clerk JWKS)",
          "rate-limiting (100 req/min/key; bursts=30)",
          "request-size-limiting (max 10MB)",
          "acl (allowlist: prod-clients)",
          "cors"
        ]
      },
      "clerk": {
        "mode": "JWT verification at gateway; user → org → roles",
        "claims_used": ["sub", "org_id", "roles", "email"]
      }
    },
    "storage_cdn": {
      "provider": "Local disk in dev; S3-compatible (e.g., Cloudflare R2) in prod",
      "cdn": "Dev: served via /static; Prod: CDN signed URLs (e.g., Cloudflare)",
      "layout": ["quarantine/", "public/"],
      "signing": "Dev: none; Prod: presigned S3 URLs or Worker-signed CDN URLs (15 min TTL)"
    },
    "observability": {
      "langfuse": {
        "trace_all_llm_calls": true,
        "log": ["prompt_hash", "model", "latency_ms", "cost_usd", "tokens", "guardrails_status"]
      },
      "metrics": ["p95_latency", "image_success_rate", "cache_hit_rate", "openrouter_4xx_5xx", "cost_per_job"]
    },
    "evaluation": {
      "guardrails": {
        "contracts": [
          "guardrails/render_plan.json",
          "guardrails/canon.json",
          "guardrails/critique.json"
        ],
        "on_fail": "reject_request_with_422"
      }
    },
    "security": {
      "secrets": "mounted at /secrets; never log",
      "pii": "no storage of raw user PII beyond Clerk subject",
      "content_filters": ["NSFW", "hate/violence terms blacklist", "logo misuse detector"],
      "audit": "append-only audit table for renders"
    }
  },
  "schemas": {
    "RenderRequest": {
      "type": "object",
      "required": ["project_id", "prompts", "outputs"],
      "properties": {
        "project_id": { "type": "string" },
        "prompts": {
          "type": "object",
          "required": ["task"],
          "properties": {
            "task": { "type": "string", "enum": ["create","edit","variations"] },
            "instruction": { "type": "string", "minLength": 5 },
            "references": {
              "type": "array",
              "items": { "type": "string", "description": "R2 object keys or https URLs on allowlisted CDN domains (https only)" },
              "maxItems": 8
            }
          }
        },
        "outputs": {
          "type": "object",
          "required": ["count","format","dimensions"],
          "properties": {
            "count": { "type": "integer", "minimum": 1, "maximum": 6 },
            "format": { "type": "string", "enum": ["png","jpg","webp"] },
            "dimensions": { "type": "string", "pattern": "^[0-9]{2,5}x[0-9]{2,5}$" }
          }
        },
        "constraints": {
          "type": "object",
          "properties": {
            "palette_hex": { "type": "array", "items": { "type": "string", "pattern": "^#([0-9a-fA-F]{6})$" }, "maxItems": 12 },
            "fonts": { "type": "array", "items": { "type": "string" }, "maxItems": 6 },
            "logo_safe_zone_pct": { "type": "number", "minimum": 0, "maximum": 40 }
          }
        }
      }
    },
    "RenderResponse": {
      "type": "object",
      "required": ["assets", "audit"],
      "properties": {
        "assets": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["url"],
            "properties": {
              "url": { "type": "string" },
              "synthid": { "type": "object", "properties": { "present": { "type": "boolean" }, "payload": { "type": "string" } } }
            }
          }
        },
        "audit": {
          "type": "object",
          "properties": {
            "trace_id": { "type": "string" },
            "model_route": { "type": "string" },
            "cost_usd": { "type": "number" },
            "guardrails_ok": { "type": "boolean" },
            "verified_by": { "type": "string", "enum": ["declared", "external", "none"] }
          }
        }
      }
    },
    "IngestRequest": {
      "type": "object",
      "required": ["project_id", "assets"],
      "properties": {
        "project_id": { "type": "string" },
        "assets": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 50
        }
      }
    },
    "IngestResponse": {
      "type": "object",
      "properties": {
        "processed": { "type": "integer" },
        "qdrant_ids": { "type": "array", "items": { "type": "string" } }
      }
    },
    "CanonDeriveRequest": {
      "type": "object",
      "required": ["project_id", "evidence_ids"],
      "properties": {
        "project_id": { "type": "string" },
        "evidence_ids": { "type": "array", "items": { "type": "string" } }
      }
    },
    "CanonDeriveResponse": {
      "type": "object",
      "properties": {
        "palette_hex": { "type": "array", "items": { "type": "string" } },
        "fonts": { "type": "array", "items": { "type": "string" } },
        "voice": { "type": "object", "properties": { "tone": { "type": "string" }, "dos": { "type": "array", "items": { "type": "string" } }, "donts": { "type": "array", "items": { "type": "string" } } } }
      }
    },
    "CritiqueRequest": {
      "type": "object",
      "required": ["project_id", "asset_ids"],
      "properties": {
        "project_id": { "type": "string" },
        "asset_ids": { "type": "array", "items": { "type": "string" } }
      }
    },
    "CritiqueResponse": {
      "type": "object",
      "properties": {
        "score": { "type": "number", "minimum": 0, "maximum": 1 },
        "violations": { "type": "array", "items": { "type": "string" } },
        "repair_suggestions": { "type": "array", "items": { "type": "string" } }
      }
    }
  },
  "guardrails_contracts": {
    "render_plan.json": {
      "type": "object",
      "required": ["goal","ops","safety"],
      "properties": {
        "goal": { "type": "string", "minLength": 5 },
        "ops": {
          "type": "array",
          "items": { "type": "string", "enum": ["local_edit","inpaint","style_transfer","multi_image_fusion","text_overlay"] }
        },
        "safety": {
          "type": "object",
          "properties": {
            "respect_logo_safe_zone": { "type": "boolean" },
            "palette_only": { "type": "boolean" }
          }
        }
      }
    },
    "canon.json": {
      "type": "object",
      "required": ["palette_hex","fonts","voice"],
      "properties": {
        "palette_hex": { "type": "array", "items": { "type": "string", "pattern": "^#([0-9a-fA-F]{6})$" }, "minItems": 2 },
        "fonts": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
        "voice": { "type": "object", "required": ["tone"], "properties": { "tone": { "type": "string" }, "dos": { "type": "array", "items": { "type": "string" } }, "donts": { "type": "array", "items": { "type": "string" } } } }
      }
    },
    "critique.json": {
      "type": "object",
      "required": ["score","violations"],
      "properties": {
        "score": { "type": "number", "minimum": 0, "maximum": 1 },
        "violations": { "type": "array", "items": { "type": "string" } },
        "repair_suggestions": { "type": "array", "items": { "type": "string" } }
      }
    }
  },
  "kong_config": {
    "file": "infra/kong/kong.yaml",
    "services": [
      { "name": "sgd-api", "url": "http://api:8000" }
    ],
    "routes": [
      { "name": "sgd-api-route", "service": "sgd-api", "paths": ["/"], "strip_path": false }
    ],
    "plugins": [
      { "name": "openid-connect", "config": { "issuer": "https://clerk.your-domain", "discovery": true, "bearer_only": true, "scopes_required": [], "verify_parameters": ["exp"], "set_access_token_header": true, "upstream_headers": ["X-User-Sub: sub", "X-Org-Id: org_id", "X-User-Roles: roles"] } },
      { "name": "rate-limiting", "config": { "second": 10, "minute": 100, "policy": "redis", "limit_by": "credential", "redis_host": "redis", "redis_port": 6379, "redis_database": 0 } },
      { "name": "request-size-limiting", "config": { "allowed_payload_size": 50 } },
      { "name": "cors", "config": { "origins": ["*"], "methods": ["GET","POST"], "headers": ["Authorization","Content-Type"], "credentials": false } }
    ]
  },
  "docker_compose": {
    "file": "docker-compose.yml",
    "services": {
      "api": {
        "build": "./api",
        "ports": ["8000:8000"],
        "env_file": ".env",
        "depends_on": ["redis","qdrant","postgres"]
      },
      "kong": {
        "image": "kong:3.7",
        "ports": ["8001:8001","8000:8000"],
        "volumes": ["./infra/kong/kong.yaml:/usr/local/kong/declarative/kong.yml"],
        "environment": {
          "KONG_DATABASE": "off",
          "KONG_DECLARATIVE_CONFIG": "/usr/local/kong/declarative/kong.yml",
          "KONG_PROXY_ACCESS_LOG": "/dev/stdout",
          "KONG_ADMIN_ACCESS_LOG": "/dev/stdout",
          "KONG_PROXY_ERROR_LOG": "/dev/stderr",
          "KONG_ADMIN_ERROR_LOG": "/dev/stderr"
        }
      },
      "redis": { "image": "redis:7-alpine", "ports": ["6379:6379"] },
      "qdrant": { "image": "qdrant/qdrant:v1.11.0", "ports": ["6333:6333"] },
      "postgres": { "image": "postgres:16-alpine", "ports": ["5432:5432"], "environment": { "POSTGRES_PASSWORD": "postgres" } },
      "langfuse": { "image": "ghcr.io/langfuse/langfuse:latest", "ports": ["3001:3000"] }
    }
  },
  "openapi": {
    "file": "api/openapi.yaml",
    "summary": "Defines /render, /ingest, /canon/derive, /critique, /healthz, /metrics with schemas referenced above"
  },
  "prompts": {
    "planner": "System: You are a senior brand designer… Use Brand Canon strictly. Output must satisfy guardrails/render_plan.json.",
    "critic": "System: You are a brand QA auditor. Compare asset against Brand Canon. Output schema=guardrails/critique.json. Be strict.",
    "canon_extractor": "System: Extract palette hexes (max 12), primary/secondary fonts, and voice dos/donts from provided evidence. Schema=guardrails/canon.json."
  },
  "testing": {
    "unit": [
      "Schema validation tests for all request/response",
      "OpenRouter client mocks for planner/critic/image"
    ],
    "integration": [
      "Happy path /render with 2 references, 2 outputs",
      "Guardrails failure paths (invalid palette, missing tone)",
      "Rate-limit enforcement via Kong (burst/exceed)",
      "JWT invalid/expired token",
      "Redis embed cache hit/miss stats",
      "Qdrant insert/search round-trip"
    ],
    "load": [
      "Soak test /render at 5 rps, p95<1800ms excluding image call",
      "Spike test 50 rps for 60s; no 5xx from API"
    ],
    "security": [
      "JWT no-scope → 403",
      "R2 signed URL expiry respected",
      "PII redaction in logs",
      "SSRF guard on reference URLs"
    ],
    "artifacts": [
      "reports/pytest.xml",
      "reports/k6.html",
      "reports/owasp_zap.md"
    ]
  },
  "performance_targets": {
    "api_p95_ms": 600,
    "image_success_rate": 0.98,
    "cache_hit_rate_embeddings": 0.5,
    "cost_per_render_usd": 0.06,
    "error_budget_monthly_pct": 1.0
  },
  "ci_cd": {
    "pipeline": [
      "Lint & typecheck",
      "Unit tests",
      "Contract tests (Guardrails)",
      "Integration tests (Docker Compose up)",
      "Security scan (pip-audit, trivy)",
      "Build & push images",
      "Deploy (optional K8s manifests)",
      "Smoke tests: /healthz, /metrics"
    ]
  },
  "runbooks": {
    "oncall": [
      "OpenRouter 5xx > 3% for 5m → fail over to fallback models; reduce concurrency by 50%",
      "Image generation latency > 45s p95 → throttle /render to 3 rps/key, queue rest",
      "Redis down → disable embed cache; continue with local embedding",
      "Qdrant down → read-only mode; block ingest"
    ],
    "rollback": [
      "Revert Kong config (git-tagged)",
      "Redeploy previous api image",
      "Restore .env from last backup",
      "Invalidate CDN keys for broken assets"
    ]
  },
  "acceptance_criteria": [
    "AC1: /render produces at least one image via Gemini 2.5 Flash Image; audit.verified_by present and one of declared|external|none; response matches RenderResponse schema.",
    "AC2: Guardrails rejects malformed plans with 422.",
    "AC3: Kong enforces per-key 100 req/min and JWT verification; invalid tokens blocked.",
    "AC4: Redis cache demonstrates ≥40% hit rate in synthetic repeat-embed test.",
    "AC5: Langfuse traces exist for planner, critic, image calls with cost/tokens.",
    "AC6: R2 assets retrievable via signed CDN URLs; expire after TTL.",
    "AC7: Ingest processes PDF → Canon JSON; Qdrant search returns relevant items.",
    "AC8: Tenant isolation enforced across Qdrant (per-org collections), Postgres (RLS), and R2 (org-prefixed keys).",
    "AC9: Upload promotion requires AV clean, MIME allowlist pass, and EXIF strip; failures remain in quarantine.",
    "AC10: Per-org budget caps enforced; 50/80/100% alerts emitted; over-cap requests receive 429 with Retry-After."
  ],
  "agent_instructions": {
    "order_of_work": [
      "Scaffold repo per repository_layout",
      "Implement OpenRouter client with policy file",
      "Build /render endpoint end-to-end (no stubs)",
      "Wire Guardrails contracts (render_plan first)",
      "Integrate R2 upload + signed URL Worker",
      "Add Langfuse tracing wrappers",
      "Add Kong declarative config + Clerk JWKS",
      "Implement ingest pipeline (Unstructured → DocAI → Canon)",
      "Add Redis embed cache + local bge-m3 embeddings",
      "Add Qdrant upsert/query",
      "Write tests (unit → integration → load)",
      "Provision CI with the gates in ci_cd",
      "Run acceptance_criteria and export proofs"
    ],
    "hard_fail_on": [
      "Any TODO/FIXME",
      "Unhandled exceptions in endpoints",
      "Logging secrets",
      "Missing Guardrails validation calls",
      "No tests for /render happy path"
    ],
    "artifacts_expected": [
      "OpenAPI file",
      "Guardrails contracts",
      "Langfuse traces (ids in test output)",
      "Kong config applied",
      "Signed URL download proof",
      "AC1–AC7 proof log JSON"
    ]
  },
  "snippets": {
    "fastapi_main_py": "from fastapi import FastAPI
app = FastAPI()
@app.get('/healthz')
def health():
    return {'ok': True}
",
    "openrouter_call": "def call_openrouter(model, messages, **kw):
    import httpx, os
    r = httpx.post('https://openrouter.ai/api/v1/chat/completions', headers={'Authorization': f'Bearer {os.environ[\"OPENROUTER_API_KEY\"]}', 'HTTP-Referer': 'https://yourapp', 'X-Title': 'sgd-api'}, json={'model': model, 'messages': messages, **kw}, timeout=20.0)
    r.raise_for_status(); return r.json()",
    "gemini_image_call": "def gen_image(prompt):
    return call_openrouter('openrouter/gemini-2.5-flash-image', [{'role':'user','content':prompt}])",
    "redis_cache": "def cache_get_set(client, key, factory, ttl=86400):
    import json
    v = client.get(key)
    if v: return json.loads(v)
    v = factory(); client.setex(key, ttl, json.dumps(v)); return v"
  },
  "risk_register": [
    { "risk": "OpenRouter latency/quotas", "mitigation": "fallbacks + backoff; budget caps per task" },
    { "risk": "DocAI region/limits", "mitigation": "batch ingest throttling; partial parse via Unstructured only" },
    { "risk": "R2 signed URL abuse", "mitigation": "short TTL; scope keys; IP rate limits via CDN rules" }
  ],
  "rollout_plan": [
    "Phase 0: /render MVP behind Kong, internal allowlist only",
    "Phase 1: Ingest + Canon; Redis+Qdrant live; Langfuse dashboards",
    "Phase 2: External beta (10 clients), SLOs enforced, alerts active",
    "Phase 3: General availability"
  ]
}