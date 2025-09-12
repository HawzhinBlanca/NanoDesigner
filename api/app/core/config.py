from __future__ import annotations

import os
from dataclasses import dataclass


def getenv(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v


@dataclass
class Settings:
    # Service
    service_name: str = getenv("SERVICE_NAME", "sgd-api") or "sgd-api"
    service_env: str = getenv("SERVICE_ENV", "dev") or "dev"
    service_region: str = getenv("SERVICE_REGION", "eu-central") or "eu-central"
    log_level: str = getenv("LOG_LEVEL", "INFO") or "INFO"

    # External endpoints/keys
    openrouter_api_key: str | None = getenv("OPENROUTER_API_KEY")
    
    # OpenRouter timeout configurations (in seconds)
    openrouter_timeout: int = int(getenv("OPENROUTER_TIMEOUT", "30") or "30")  # Increased minimum
    openrouter_timeout_long: int = int(getenv("OPENROUTER_TIMEOUT_LONG", "120") or "120")  # For complex operations
    openrouter_timeout_streaming: int = int(getenv("OPENROUTER_TIMEOUT_STREAMING", "300") or "300")  # For streaming
    min_timeout_seconds: int = int(getenv("MIN_TIMEOUT_SECONDS", "3") or "3")  # Minimum timeout for production
    
    langfuse_public_key: str | None = getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = getenv("LANGFUSE_SECRET_KEY")
    langfuse_host: str = getenv("LANGFUSE_HOST", "https://cloud.langfuse.com") or "https://cloud.langfuse.com"

    redis_url: str = getenv("REDIS_URL", "redis://localhost:6379/0") or "redis://localhost:6379/0"
    qdrant_url: str = getenv("QDRANT_URL", "http://localhost:6333") or "http://localhost:6333"
    qdrant_api_key: str | None = getenv("QDRANT_API_KEY")

    # Database
    database_url: str = getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres") or "postgresql://postgres:postgres@localhost:5432/postgres"

    # Cloudflare R2 (S3 compatible)
    r2_account_id: str | None = getenv("R2_ACCOUNT_ID")
    r2_access_key_id: str | None = getenv("R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = getenv("R2_SECRET_ACCESS_KEY")
    r2_bucket: str = getenv("R2_BUCKET", "assets") or "assets"
    # Generic storage
    storage_backend: str = getenv("STORAGE_BACKEND", "auto") or "auto"
    local_storage_dir: str = getenv("LOCAL_STORAGE_DIR", "var/storage") or "var/storage"
    service_base_url: str = getenv("SERVICE_BASE_URL", "http://localhost:8000") or "http://localhost:8000"
    # Optional signed-URL worker
    cf_account_id: str | None = getenv("CLOUDFLARE_ACCOUNT_ID")
    cf_worker_signer_secret: str | None = getenv("CLOUDFLARE_WORKER_SIGNER_SECRET")

    # Google Doc AI / ingest
    google_application_credentials: str | None = getenv("GOOGLE_APPLICATION_CREDENTIALS")
    doc_ai_processor_id: str | None = getenv("DOC_AI_PROCESSOR_ID")

    # Auth via Kong + Clerk
    clerk_jwks_url: str | None = getenv("CLERK_JWKS_URL")
    kong_admin_url: str | None = getenv("KONG_ADMIN_URL")

    # E2E Configuration
    rate_limit_rpm: int = int(getenv("RATE_LIMIT_RPM", "100") or "100")
    rate_limit_burst: int = int(getenv("RATE_LIMIT_BURST", "20") or "20")
    
    # Cache Configuration
    cache_default_ttl: int = int(getenv("CACHE_DEFAULT_TTL", "3600") or "3600")  # 1 hour
    cache_plan_ttl: int = int(getenv("CACHE_PLAN_TTL", "86400") or "86400")  # 24 hours
    cache_embed_ttl: int = int(getenv("CACHE_EMBED_TTL", "604800") or "604800")  # 7 days
    enable_e2e_monitoring: bool = (getenv("ENABLE_E2E_MONITORING", "true") or "true").lower() == "true"
    enable_journey_optimization: bool = (getenv("ENABLE_JOURNEY_OPTIMIZATION", "true") or "true").lower() == "true"
    enable_error_experience: bool = (getenv("ENABLE_ERROR_EXPERIENCE", "true") or "true").lower() == "true"
    enable_performance_optimization: bool = (getenv("ENABLE_PERFORMANCE_OPTIMIZATION", "true") or "true").lower() == "true"
    e2e_analytics_retention_days: int = int(getenv("E2E_ANALYTICS_RETENTION_DAYS", "30") or "30")
    performance_optimization_interval_minutes: int = int(getenv("PERFORMANCE_OPTIMIZATION_INTERVAL_MINUTES", "60") or "60")

    # Security & policy
    cors_allow_origins: str | None = getenv("CORS_ALLOW_ORIGINS")
    enable_inapp_rate_limit: bool = (getenv("ENABLE_INAPP_RATE_LIMIT", "true") or "true").lower() == "true"
    enable_inapp_auth: bool = (getenv("ENABLE_INAPP_AUTH", "false") or "false").lower() == "true"
    ref_url_allow_hosts: str | None = getenv("REF_URL_ALLOW_HOSTS")


settings = Settings()
