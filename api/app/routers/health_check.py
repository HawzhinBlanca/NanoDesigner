"""
Comprehensive health check endpoint for production monitoring
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import asyncio
import time
import psutil
import redis
import httpx
from datetime import datetime
import os

router = APIRouter(tags=["health"])

class HealthChecker:
    """Performs comprehensive health checks on all system components"""
    
    @staticmethod
    async def check_redis() -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            start = time.time()
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            
            # Test basic operations
            test_key = f"health_check_{int(time.time())}"
            r.setex(test_key, 10, "test")
            value = r.get(test_key)
            r.delete(test_key)
            
            latency = (time.time() - start) * 1000
            
            # Get Redis info
            info = r.info()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @staticmethod
    async def check_postgres() -> Dict[str, Any]:
        """Check PostgreSQL connectivity"""
        try:
            import asyncpg
            start = time.time()
            
            conn = await asyncpg.connect(os.getenv("DATABASE_URL", ""))
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            
            latency = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": version.split()[1] if version else "unknown"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @staticmethod
    async def check_qdrant() -> Dict[str, Any]:
        """Check Qdrant vector database"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.get(
                    f"{os.getenv('QDRANT_URL', 'http://localhost:6333')}/collections",
                    timeout=5.0
                )
                latency = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "healthy",
                        "latency_ms": round(latency, 2),
                        "collections": len(data.get("result", {}).get("collections", []))
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "http_status": response.status_code
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @staticmethod
    async def check_openrouter() -> Dict[str, Any]:
        """Check OpenRouter API availability"""
        try:
            if not os.getenv("OPENROUTER_API_KEY"):
                return {
                    "status": "not_configured",
                    "message": "OpenRouter API key not set"
                }
            
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
                    },
                    timeout=10.0
                )
                latency = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "healthy",
                        "latency_ms": round(latency, 2),
                        "available_models": len(data.get("data", []))
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "http_status": response.status_code
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @staticmethod
    def check_system_resources() -> Dict[str, Any]:
        """Check system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network I/O
            net_io = psutil.net_io_counters()
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "used_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "used_percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                },
                "network": {
                    "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                    "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2)
                }
            }
        except Exception as e:
            return {"error": str(e)}

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": os.getenv("SERVICE_NAME", "sgd-api"),
        "environment": os.getenv("SERVICE_ENV", "development"),
        "version": os.getenv("APP_VERSION", "1.0.0")
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Comprehensive health check with all dependencies"""
    
    start_time = time.time()
    checker = HealthChecker()
    
    # Run all checks in parallel
    checks = await asyncio.gather(
        checker.check_redis(),
        checker.check_postgres(),
        checker.check_qdrant(),
        checker.check_openrouter(),
        return_exceptions=True
    )
    
    # Process results
    redis_status = checks[0] if not isinstance(checks[0], Exception) else {"status": "error", "error": str(checks[0])}
    postgres_status = checks[1] if not isinstance(checks[1], Exception) else {"status": "error", "error": str(checks[1])}
    qdrant_status = checks[2] if not isinstance(checks[2], Exception) else {"status": "error", "error": str(checks[2])}
    openrouter_status = checks[3] if not isinstance(checks[3], Exception) else {"status": "error", "error": str(checks[3])}
    
    # Get system resources
    system_resources = checker.check_system_resources()
    
    # Determine overall health
    critical_services = [redis_status, postgres_status]
    overall_healthy = all(
        service.get("status") in ["healthy", "not_configured"] 
        for service in critical_services
    )
    
    # Calculate total check time
    total_time_ms = (time.time() - start_time) * 1000
    
    response = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": os.getenv("SERVICE_NAME", "sgd-api"),
        "environment": os.getenv("SERVICE_ENV", "development"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "uptime_seconds": time.time() - getattr(health_check, 'start_time', time.time()),
        "check_duration_ms": round(total_time_ms, 2),
        "dependencies": {
            "redis": redis_status,
            "postgres": postgres_status,
            "qdrant": qdrant_status,
            "openrouter": openrouter_status
        },
        "system": system_resources
    }
    
    # Return appropriate status code
    if not overall_healthy:
        raise HTTPException(status_code=503, detail=response)
    
    return response

@router.get("/health/live")
async def liveness_probe() -> Dict[str, Any]:
    """Kubernetes liveness probe - checks if service is alive"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@router.get("/health/ready")
async def readiness_probe() -> Dict[str, Any]:
    """Kubernetes readiness probe - checks if service can handle requests"""
    
    checker = HealthChecker()
    
    # Check critical dependencies
    redis_check = await checker.check_redis()
    
    if redis_check.get("status") != "healthy":
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "reason": "Redis unavailable"}
        )
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }

# Store start time for uptime calculation
health_check.start_time = time.time()