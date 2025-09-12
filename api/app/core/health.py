"""Comprehensive health check system for production readiness.

This module provides detailed health checks for all system dependencies
and components, ensuring the application is fully operational.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import httpx
from redis import Redis
from qdrant_client import QdrantClient
import boto3
from sqlalchemy import create_engine, text

from ..core.config import settings
from ..core.structured_logging import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.now)
    
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "error": self.error,
            "last_check": self.last_check.isoformat()
        }


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self):
        self.checks: List[ComponentHealth] = []
        self.last_full_check: Optional[datetime] = None
        self.cache_duration = timedelta(seconds=10)
        self._cached_results: Optional[Dict[str, Any]] = None
        
    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        start = time.time()
        try:
            engine = create_engine(
                f"postgresql://{settings.db_user}:{settings.db_password}@"
                f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
            )
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Check connection pool
                pool_size = engine.pool.size()
                pool_checked_out = engine.pool.checked_out_connections
                
            response_time = (time.time() - start) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "pool_size": pool_size,
                    "connections_in_use": pool_checked_out,
                    "host": settings.db_host,
                    "database": settings.db_name
                }
            )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and performance."""
        start = time.time()
        try:
            redis = Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True
            )
            
            # Ping Redis
            redis.ping()
            
            # Get memory info
            info = redis.info("memory")
            memory_used = info.get("used_memory_human", "unknown")
            
            # Check response time with a simple operation
            test_key = "__health_check__"
            redis.setex(test_key, 10, "healthy")
            value = redis.get(test_key)
            
            response_time = (time.time() - start) * 1000
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "memory_used": memory_used,
                    "connected_clients": info.get("connected_clients", 0),
                    "host": settings.redis_host
                }
            )
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def check_qdrant(self) -> ComponentHealth:
        """Check Qdrant vector database connectivity."""
        start = time.time()
        try:
            client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )
            
            # Get collections info
            collections = client.get_collections()
            collection_count = len(collections.collections)
            
            response_time = (time.time() - start) * 1000
            return ComponentHealth(
                name="qdrant",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "collections": collection_count,
                    "host": settings.qdrant_host
                }
            )
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return ComponentHealth(
                name="qdrant",
                status=HealthStatus.DEGRADED,  # Degraded since vector search is not critical
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def check_s3(self) -> ComponentHealth:
        """Check S3/R2 storage connectivity."""
        start = time.time()
        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key
            )
            
            # List buckets to verify connectivity
            response = s3_client.list_buckets()
            bucket_count = len(response.get("Buckets", []))
            
            # Try to head the main bucket
            s3_client.head_bucket(Bucket=settings.r2_bucket)
            
            response_time = (time.time() - start) * 1000
            return ComponentHealth(
                name="s3_storage",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "bucket": settings.r2_bucket,
                    "total_buckets": bucket_count,
                    "endpoint": settings.s3_endpoint_url
                }
            )
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return ComponentHealth(
                name="s3_storage",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def check_openrouter(self) -> ComponentHealth:
        """Check OpenRouter API connectivity."""
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                    timeout=5.0
                )
                response.raise_for_status()
                
            response_time = (time.time() - start) * 1000
            return ComponentHealth(
                name="openrouter",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "endpoint": "openrouter.ai",
                    "status_code": response.status_code
                }
            )
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return ComponentHealth(
                name="openrouter",
                status=HealthStatus.DEGRADED,  # Degraded allows read operations
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def check_system_resources(self) -> ComponentHealth:
        """Check system resources (CPU, memory, disk)."""
        start = time.time()
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            # Determine health based on resource usage
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 85:
                status = HealthStatus.DEGRADED
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"Critical disk usage: {disk.percent}%")
            
            response_time = (time.time() - start) * 1000
            return ComponentHealth(
                name="system_resources",
                status=status,
                response_time_ms=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "warnings": warnings
                }
            )
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def check_all(self, use_cache: bool = True) -> Dict[str, Any]:
        """Run all health checks."""
        # Check cache
        if use_cache and self._cached_results and self.last_full_check:
            if datetime.now() - self.last_full_check < self.cache_duration:
                return self._cached_results
        
        # Run all checks concurrently
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_qdrant(),
            self.check_s3(),
            self.check_openrouter(),
            self.check_system_resources(),
            return_exceptions=True
        )
        
        # Process results
        components = []
        overall_status = HealthStatus.HEALTHY
        total_response_time = 0
        
        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check failed with exception: {check}")
                component = ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    error=str(check)
                )
            else:
                component = check
            
            components.append(component.to_dict())
            total_response_time += component.response_time_ms
            
            # Determine overall status
            if component.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif component.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        result = {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "total_response_time_ms": total_response_time,
            "components": components,
            "version": settings.service_version,
            "environment": settings.service_env
        }
        
        # Cache results
        self._cached_results = result
        self.last_full_check = datetime.now()
        
        # Log health status
        logger.info(
            "Health check completed",
            status=overall_status.value,
            response_time_ms=total_response_time,
            component_count=len(components)
        )
        
        return result
    
    async def check_liveness(self) -> Dict[str, Any]:
        """Simple liveness check for Kubernetes."""
        return {
            "status": "alive",
            "timestamp": datetime.now().isoformat()
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """Readiness check for load balancer."""
        # Quick checks for critical components only
        critical_checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            return_exceptions=True
        )
        
        for check in critical_checks:
            if isinstance(check, Exception) or check.status == HealthStatus.UNHEALTHY:
                return {
                    "ready": False,
                    "timestamp": datetime.now().isoformat(),
                    "reason": str(check) if isinstance(check, Exception) else check.error
                }
        
        return {
            "ready": True,
            "timestamp": datetime.now().isoformat()
        }


# Global health checker instance
health_checker = HealthChecker()


async def get_health_status(detailed: bool = False) -> Dict[str, Any]:
    """Get current health status."""
    if detailed:
        return await health_checker.check_all()
    return await health_checker.check_liveness()


async def get_readiness_status() -> Dict[str, Any]:
    """Get readiness status."""
    return await health_checker.check_readiness()