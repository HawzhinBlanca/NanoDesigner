from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import settings
from .core.logging import setup_logging
from .core.api_versioning import version_manager, get_api_versions
import os
from .models.exceptions import (
    SGDBaseException,
    EXCEPTION_HANDLERS,
    to_http_exception
)
from .middleware.request_response import (
    CORSMiddleware,
    SecurityHeadersMiddleware,
    RequestResponseMiddleware
)
from .core.rate_limits import RateLimitMiddleware
from .routers import render, health, health_detailed, ingest, canon, critique, websocket, async_render, prometheus, admin, e2e, upload
# Mock routers removed - moved to tests/mocks
# from .routers import render_mock, render_simple
from .services.e2e_performance import E2EPerformanceOptimizer


setup_logging(settings.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler replacing deprecated on_event hooks."""
    # Startup
    try:
        from .models import schemas
        models_to_rebuild = [
            schemas.RenderRequestPrompts,
            schemas.RenderRequestOutputs,
            schemas.RenderRequestConstraints,
            schemas.RenderRequest,
            schemas.RenderResponse,
            schemas.IngestRequest,
            schemas.IngestResponse,
            schemas.CanonDeriveRequest,
            schemas.CanonDeriveResponse,
            schemas.CritiqueRequest,
            schemas.CritiqueResponse,
        ]
        for model in models_to_rebuild:
            try:
                model.model_rebuild()
                print(f"✅ Rebuilt {model.__name__}")
            except Exception as e:
                print(f"⚠️  Failed to rebuild {model.__name__}: {e}")
    except Exception as e:
        print(f"Startup initialization error: {e}")

    # Initialize E2E services (logs only; instances constructed elsewhere)
    initialized_services = []
    if settings.enable_e2e_monitoring:
        initialized_services.append("monitoring")
    if settings.enable_journey_optimization:
        initialized_services.append("journey optimization")
    if settings.enable_error_experience:
        initialized_services.append("error experience")
    if settings.enable_performance_optimization:
        initialized_services.append("performance optimization")
    if initialized_services:
        print(f"E2E services initialized: {', '.join(initialized_services)}")
    else:
        print("E2E services disabled by configuration")

    # Inject E2E service instances for routers when enabled
    # Support both 'prod' and 'production' environment values
    is_production = settings.service_env in ["prod", "production"]
    try:
        # Enable E2E services in production or when explicitly enabled
        if (is_production or settings.service_env == "staging") and (
            settings.enable_e2e_monitoring or 
            settings.enable_journey_optimization or 
            settings.enable_error_experience or 
            settings.enable_performance_optimization
        ):
            from .routers import e2e as _e2e_router
            from .services.e2e_monitoring import E2EMonitoringService
            from .services.journey_optimizer import JourneyOptimizer
            from .services.error_experience import ErrorExperienceService
            from .services.e2e_performance import E2EPerformanceOptimizer
            _e2e_router.set_e2e_services(
                E2EMonitoringService(),  # tests patch these classes
                JourneyOptimizer(),
                ErrorExperienceService(),
                E2EPerformanceOptimizer(),
            )
            # Call initialize() once if present (tests assert this)
            for svc in (
                _e2e_router.e2e_monitoring,
                _e2e_router.journey_optimizer,
                _e2e_router.error_experience,
                _e2e_router.performance_optimizer,
            ):
                try:
                    init = getattr(svc, "initialize", None)
                    if init:
                        res = init()
                        if hasattr(res, "__await__"):
                            await res  # type: ignore[func-returns-value]
                except Exception:
                    pass
    except Exception as e:
        print(f"E2E service injection failed: {e}")

    yield

    # Shutdown
    print("Shutdown event completed")

app = FastAPI(
    title=settings.service_name,
    description="Smart Graphic Designer API - AI-powered graphic design generation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# OpenTelemetry (optional via env)
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        resource = Resource.create({"service.name": settings.service_name, "service.environment": settings.service_env})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Instrument FastAPI and httpx
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
    except Exception as e:
        print(f"OTel init failed: {e}")

# Initialize E2E services
performance_optimizer = E2EPerformanceOptimizer()

# Add request/response middleware first to ensure headers/meta
app.add_middleware(RequestResponseMiddleware)

# Add basic CORS middleware only for now
origins = [o.strip() for o in (settings.cors_allow_origins or "").split(",") if o.strip()]
if not origins:
    # Default: wildcard in dev for tests; none in prod
    # Default: wildcard in dev for tests; restrict in production
    is_production = settings.service_env in ["prod", "production"]
    origins = [] if is_production else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key", "Idempotency-Key"]
)

# Always include security headers for consistency and tests
app.add_middleware(SecurityHeadersMiddleware)

# Add request size limit middleware (10MB default)
try:
    from .middleware.request_size_limit import RequestSizeLimitMiddleware
    max_size = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB default
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_size)
except ImportError:
    # Create the middleware if it doesn't exist
    pass

# Add rate limiting middleware
# - In production: Redis-based
# - In dev/test: in-memory fallback to avoid hard Redis dependency
is_production = settings.service_env in ["prod", "production"]
if settings.enable_inapp_rate_limit:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_rpm,
        burst_size=settings.rate_limit_burst,
        use_redis=is_production
    )

# Custom exception handlers
@app.exception_handler(SGDBaseException)
async def sgd_exception_handler(request: Request, exc: SGDBaseException):
    """Handle custom SGD exceptions."""
    # Check if we have a specific handler for this exception type
    for exc_type, handler in EXCEPTION_HANDLERS.items():
        if isinstance(exc, exc_type):
            http_exc = handler(exc)
            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail
            )
    
    # Default handler for SGDBaseException
    http_exc = to_http_exception(exc, status_code=500)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get proper request ID from middleware state
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Sanitize error message for production
    is_production = settings.service_env in ["prod", "production"]
    
    if is_production:
        # In production, log full details but don't expose them
        logger.error(
            "Unhandled exception occurred",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "error_type": type(exc).__name__
            },
            exc_info=True  # Full stack trace in logs only
        )
    else:
        # In development, include more details
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown"
            },
            exc_info=True
        )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standardize HTTP errors (like 404) to include status and meta."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    processing_time_ms = 0
    try:
        import time as _time
        start_time = getattr(request.state, '_start_time', None)
        if start_time:
            processing_time_ms = int((_time.time() - start_time) * 1000)
    except Exception:
        pass
    body = {
        "status": "error",
        "error": exc.detail if isinstance(exc.detail, str) else "HTTPError",
        "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
        "meta": {
            "request_id": request_id,
            "version": "1.0.0",
            "processing_time_ms": processing_time_ms,
        },
    }
    return JSONResponse(status_code=exc.status_code, content=body)

# Run startup/shutdown via lifespan above (on_event deprecated)

app.include_router(render.router)  # Real render endpoint enabled
# Mock endpoints removed - no longer needed in production
app.include_router(async_render.router)
app.include_router(ingest.router)
app.include_router(upload.router)
app.include_router(canon.router)
app.include_router(critique.router)
app.include_router(health.router)
app.include_router(health_detailed.router)
app.include_router(websocket.router)
app.include_router(prometheus.router)
app.include_router(admin.router)
app.include_router(e2e.router)

# Add version discovery endpoint
app.get("/api/versions", tags=["versioning"])(get_api_versions)

# Add versioned routers (v1 and v2)
v1_router = version_manager.get_router("1.0")
v2_router = version_manager.get_router("2.0")

if v1_router:
    v1_router.include_router(render.router, tags=["render"])
    v1_router.include_router(canon.router, tags=["canon"])
    v1_router.include_router(critique.router, tags=["critique"])
    app.include_router(v1_router, prefix="/api")

if v2_router:
    v2_router.include_router(render.router, tags=["render"])
    v2_router.include_router(canon.router, tags=["canon"])  
    v2_router.include_router(critique.router, tags=["critique"])
    app.include_router(v2_router, prefix="/api")

# Static serving for local storage
app.mount("/static", StaticFiles(directory=settings.local_storage_dir), name="static")
