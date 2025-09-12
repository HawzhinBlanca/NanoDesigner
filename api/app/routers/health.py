import time
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import psutil

logger = logging.getLogger(__name__)
router = APIRouter()

# Real metrics tracking
_start_time = time.time()

@router.get("/healthz")
async def health():
    """Health check with real dependency verification."""
    try:
        # Check Redis connectivity (sync ping)
        from ..services.redis import get_redis_client
        redis_client = get_redis_client()
        redis_client.ping()
        redis_healthy = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        redis_healthy = False
        
    try:
        # Check database connectivity
        from ..core.database import get_db_health
        db_healthy = await get_db_health()
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_healthy = False
        
    # Skip external OpenRouter health in dev/test to keep healthz fast
    try:
        from ..core.config import settings
        if settings.service_env in {"dev", "test"}:
            openrouter_healthy = True
        else:
            from ..services.openrouter import health_check as openrouter_health
            openrouter_healthy = await openrouter_health()
    except Exception as e:
        logger.warning(f"OpenRouter health check failed: {e}")
        openrouter_healthy = False
        
    if not all([redis_healthy, db_healthy, openrouter_healthy]):
        return {
            "ok": False, 
            "status": "degraded",
            "services": {
                "redis": redis_healthy,
                "database": db_healthy,
                "openrouter": openrouter_healthy
            }
        }
    
    return {"ok": True, "status": "healthy"}

@router.get("/metrics/json")
async def metrics() -> Dict[str, Any]:
    """JSON metrics for internal dashboards and smoke tests."""
    try:
        # Get real Prometheus metrics
        from ..core.monitoring import get_prometheus_metrics
        prometheus_metrics = await get_prometheus_metrics()
        
        # Calculate real P95 latency from stored metrics
        from ..services.redis import get_redis_client
        redis_client = get_redis_client()
        
        # Get latency percentiles from Redis samples (sorted set)
        latency_data = redis_client.zrevrange("latency_samples", 0, -1, withscores=True)
        if latency_data:
            latencies = [float(score) for _, score in latency_data]
            latencies.sort()
            p95_index = int(0.95 * len(latencies))
            p95_latency = latencies[p95_index] if latencies else 0.0
        else:
            p95_latency = 0.0
        
        # Calculate real success rate from counters
        total_requests = prometheus_metrics.get("http_requests_total", 0)
        failed_requests = prometheus_metrics.get("http_requests_failed_total", 0)
        success_rate = (total_requests - failed_requests) / max(total_requests, 1)
        
        # Get image generation metrics
        image_total = prometheus_metrics.get("image_generation_total", 0)
        image_success = prometheus_metrics.get("image_generation_success_total", 0)
        image_success_rate = image_success / max(image_total, 1)
        
        # Calculate uptime
        uptime = time.time() - _start_time
        
        # Get system metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0)
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": int(total_requests),
            "p95_latency_ms": round(p95_latency, 2),
            "image_success_rate": round(image_success_rate, 4),
            "overall_success_rate": round(success_rate, 4),
            "active_connections": prometheus_metrics.get("active_connections", 0),
            "memory_usage_mb": round(memory.used / 1024 / 1024, 2),
            "memory_usage_percent": memory.percent,
            "cpu_usage_percent": cpu_percent,
            "redis_connected": prometheus_metrics.get("redis_connected", False),
            "database_connected": prometheus_metrics.get("database_connected", False),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics unavailable: {str(e)}")
