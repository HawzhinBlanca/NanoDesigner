from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging import setup_logging
from .models.exceptions import (
    SGDBaseException,
    EXCEPTION_HANDLERS,
    to_http_exception
)
from .middleware.request_response import (
    RequestResponseMiddleware,
    CORSMiddleware,
    SecurityHeadersMiddleware,
    RateLimitingMiddleware
)
from .routers import render, health, ingest, canon, critique, websocket, async_render, prometheus, admin, e2e
from .services.startup import run_startup_tasks
from .services.worker_manager import worker_manager
from .services.e2e_monitoring import E2EMonitoringService
from .services.journey_optimizer import JourneyOptimizer
from .services.error_experience import ErrorExperienceService
from .services.e2e_performance import E2EPerformanceOptimizer


setup_logging(settings.log_level)
app = FastAPI(
    title=settings.service_name,
    description="Smart Graphic Designer API - AI-powered graphic design generation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize E2E services
e2e_monitoring = E2EMonitoringService()
journey_optimizer = JourneyOptimizer()
error_experience = ErrorExperienceService()
performance_optimizer = E2EPerformanceOptimizer()

# Add middleware stack (order matters - first added is outermost)
app.add_middleware(
    RequestResponseMiddleware,
    add_request_id=True,
    log_requests=True,
    log_responses=True,
    include_processing_time=True
)

origins = [o.strip() for o in (settings.cors_allow_origins or "").split(",") if o.strip()]
if not origins:
    # Default: lock down in non-dev; allow all in dev
    origins = ["*"] if settings.service_env == "dev" else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"]
)

app.add_middleware(SecurityHeadersMiddleware)

if settings.enable_inapp_rate_limit:
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=settings.rate_limit_rpm,
        burst_size=settings.rate_limit_burst
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
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "request_id": str(id(request))  # Simple request ID
        }
    )

# Run startup tasks
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    run_startup_tasks()
    await worker_manager.start_manager()
    
    # Initialize E2E services based on configuration
    initialized_services = []
    
    # Services are already initialized when instantiated
    if settings.enable_e2e_monitoring:
        initialized_services.append("monitoring")
    
    if settings.enable_journey_optimization:
        initialized_services.append("journey optimization")
    
    if settings.enable_error_experience:
        initialized_services.append("error experience")
    
    if settings.enable_performance_optimization:
        initialized_services.append("performance optimization")
    
    # Set E2E service instances in router (pass None for disabled services)
    e2e.set_e2e_services(
        e2e_monitoring if settings.enable_e2e_monitoring else None,
        journey_optimizer if settings.enable_journey_optimization else None,
        error_experience if settings.enable_error_experience else None,
        performance_optimizer if settings.enable_performance_optimization else None
    )
    
    if initialized_services:
        print(f"E2E services initialized: {', '.join(initialized_services)}")
    else:
        print("E2E services disabled by configuration")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await worker_manager.stop_manager()
    
    # Cleanup E2E services based on configuration
    # Note: Services don't have cleanup methods currently
    pass

app.include_router(render.router)
app.include_router(async_render.router)
app.include_router(ingest.router)
app.include_router(canon.router)
app.include_router(critique.router)
app.include_router(health.router)
app.include_router(websocket.router)
app.include_router(prometheus.router)
app.include_router(admin.router)
app.include_router(e2e.router)

# Static serving for local storage
app.mount("/static", StaticFiles(directory=settings.local_storage_dir), name="static")
