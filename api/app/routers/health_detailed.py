"""
Comprehensive health check endpoints for monitoring
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
import asyncio
import time
import psutil
import os
from datetime import datetime, timedelta
import httpx
from ..services.redis import get_redis_client
from ..core.config import settings

router = APIRouter(prefix="/health", tags=["health"])

# Track service start time
SERVICE_START_TIME = datetime.now()

async def check_database() -> Dict[str, Any]:
    """Check database connectivity and performance"""
    try:
        start = time.time()
        # Simple database ping (implement based on your DB)
        # For now, just simulate
        await asyncio.sleep(0.01)  # Simulate DB query
        latency = (time.time() - start) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "connection_pool": {
                "active": 5,
                "idle": 10,
                "total": 15
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity and performance"""
    try:
        redis = await get_redis_client()
        start = time.time()
        
        # Ping Redis
        await redis.ping()
        
        # Get Redis info
        info = await redis.info()
        
        latency = (time.time() - start) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_openrouter() -> Dict[str, Any]:
    """Check OpenRouter API availability"""
    try:
        async with httpx.AsyncClient() as client:
            start = time.time()
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                timeout=5.0
            )
            latency = (time.time() - start) * 1000
            
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "latency_ms": round(latency, 2),
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_storage() -> Dict[str, Any]:
    """Check storage availability and space"""
    try:
        disk_usage = psutil.disk_usage('/')
        
        return {
            "status": "healthy" if disk_usage.percent < 90 else "warning",
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "percent_used": disk_usage.percent
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get network stats
        net_io = psutil.net_io_counters()
        
        # Get process info
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
                "process_mb": round(process_memory.rss / (1024**2), 2)
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
    except Exception as e:
        return {"error": str(e)}

def get_uptime() -> Dict[str, Any]:
    """Get service uptime information"""
    uptime_duration = datetime.now() - SERVICE_START_TIME
    days = uptime_duration.days
    hours, remainder = divmod(uptime_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return {
        "start_time": SERVICE_START_TIME.isoformat(),
        "uptime": f"{days}d {hours}h {minutes}m {seconds}s",
        "uptime_seconds": int(uptime_duration.total_seconds())
    }

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0")
    }

@router.get("/status")
async def health_status(request: Request):
    """Status endpoint used by integration tests for middleware/header checks."""
    import uuid
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    processing_time_ms = 0
    try:
        start_time = getattr(request.state, '_start_time', None)
        if start_time:
            processing_time_ms = int((time.time() - start_time) * 1000)
    except Exception:
        pass
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "meta": {
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("SERVICE_ENV", "dev"),
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": processing_time_ms,
        },
    }

@router.get("/live")
async def liveness_probe():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}

@router.get("/ready")
async def readiness_probe():
    """Kubernetes readiness probe endpoint"""
    # Check critical dependencies
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True
    )
    
    # Service is ready only if all critical checks pass
    is_ready = all(
        isinstance(check, dict) and check.get("status") == "healthy"
        for check in checks
    )
    
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready"}

@router.get("/detailed")
async def health_detailed():
    """Detailed health check with all service dependencies"""
    # Run all checks in parallel
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_openrouter(),
        check_storage(),
        return_exceptions=True
    )
    
    # Process results
    database_health = checks[0] if isinstance(checks[0], dict) else {"status": "error", "error": str(checks[0])}
    redis_health = checks[1] if isinstance(checks[1], dict) else {"status": "error", "error": str(checks[1])}
    openrouter_health = checks[2] if isinstance(checks[2], dict) else {"status": "error", "error": str(checks[2])}
    storage_health = checks[3] if isinstance(checks[3], dict) else {"status": "error", "error": str(checks[3])}
    
    # Determine overall status
    statuses = [
        database_health.get("status"),
        redis_health.get("status"),
        openrouter_health.get("status"),
        storage_health.get("status")
    ]
    
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "uptime": get_uptime(),
        "checks": {
            "database": database_health,
            "redis": redis_health,
            "openrouter": openrouter_health,
            "storage": storage_health
        },
        "metrics": get_system_metrics()
    }

@router.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    metrics_data = []
    
    # System metrics
    system_metrics = get_system_metrics()
    uptime_info = get_uptime()
    
    # Format as Prometheus metrics
    metrics_data.append(f"# HELP nanodesigner_up Service up status")
    metrics_data.append(f"# TYPE nanodesigner_up gauge")
    metrics_data.append(f"nanodesigner_up 1")
    
    metrics_data.append(f"# HELP nanodesigner_uptime_seconds Service uptime in seconds")
    metrics_data.append(f"# TYPE nanodesigner_uptime_seconds counter")
    metrics_data.append(f"nanodesigner_uptime_seconds {uptime_info['uptime_seconds']}")
    
    if 'cpu' in system_metrics:
        metrics_data.append(f"# HELP nanodesigner_cpu_usage_percent CPU usage percentage")
        metrics_data.append(f"# TYPE nanodesigner_cpu_usage_percent gauge")
        metrics_data.append(f"nanodesigner_cpu_usage_percent {system_metrics['cpu']['percent']}")
    
    if 'memory' in system_metrics:
        metrics_data.append(f"# HELP nanodesigner_memory_usage_percent Memory usage percentage")
        metrics_data.append(f"# TYPE nanodesigner_memory_usage_percent gauge")
        metrics_data.append(f"nanodesigner_memory_usage_percent {system_metrics['memory']['percent_used']}")
        
        metrics_data.append(f"# HELP nanodesigner_process_memory_mb Process memory usage in MB")
        metrics_data.append(f"# TYPE nanodesigner_process_memory_mb gauge")
        metrics_data.append(f"nanodesigner_process_memory_mb {system_metrics['memory']['process_mb']}")
    
    # Check service health
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_openrouter(),
        return_exceptions=True
    )
    
    # Database metrics
    if isinstance(checks[0], dict) and 'latency_ms' in checks[0]:
        metrics_data.append(f"# HELP nanodesigner_database_latency_ms Database latency in milliseconds")
        metrics_data.append(f"# TYPE nanodesigner_database_latency_ms gauge")
        metrics_data.append(f"nanodesigner_database_latency_ms {checks[0]['latency_ms']}")
    
    # Redis metrics
    if isinstance(checks[1], dict) and 'latency_ms' in checks[1]:
        metrics_data.append(f"# HELP nanodesigner_redis_latency_ms Redis latency in milliseconds")
        metrics_data.append(f"# TYPE nanodesigner_redis_latency_ms gauge")
        metrics_data.append(f"nanodesigner_redis_latency_ms {checks[1]['latency_ms']}")
    
    # OpenRouter metrics
    if isinstance(checks[2], dict) and 'latency_ms' in checks[2]:
        metrics_data.append(f"# HELP nanodesigner_openrouter_latency_ms OpenRouter API latency in milliseconds")
        metrics_data.append(f"# TYPE nanodesigner_openrouter_latency_ms gauge")
        metrics_data.append(f"nanodesigner_openrouter_latency_ms {checks[2]['latency_ms']}")
    
    return "\n".join(metrics_data)

@router.get("/dependencies")
async def check_dependencies():
    """Check all external service dependencies"""
    dependencies = {
        "database": await check_database(),
        "redis": await check_redis(),
        "openrouter": await check_openrouter(),
        "storage": await check_storage()
    }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "dependencies": dependencies
    }