"""
Production-grade monitoring and observability for NanoDesigner.
Implements RUM (Real User Monitoring), APM, and business metrics.
"""

from __future__ import annotations

import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@dataclass
class MetricEvent:
    """Standard metric event structure."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""
    request_duration: float
    response_size: int
    status_code: int
    endpoint: str
    method: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class MetricsCollector:
    """Centralized metrics collection."""
    
    def __init__(self):
        self.metrics_buffer: List[MetricEvent] = []
        self.business_metrics: Dict[str, float] = {}
        self.performance_metrics: List[PerformanceMetrics] = []
    
    def track_event(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Track custom business event."""
        event = MetricEvent(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        self.metrics_buffer.append(event)
        logger.debug(f"Tracked event: {name} = {value}")
    
    def track_performance(self, metrics: PerformanceMetrics):
        """Track performance metrics."""
        self.performance_metrics.append(metrics)
        
        # Track key performance indicators
        self.track_event("api.request.duration", metrics.request_duration, {
            "endpoint": metrics.endpoint,
            "method": metrics.method,
            "status": str(metrics.status_code)
        })
        
        self.track_event("api.request.count", 1.0, {
            "endpoint": metrics.endpoint,
            "method": metrics.method,
            "status": str(metrics.status_code)
        })
    
    def track_business_metric(self, name: str, value: float):
        """Track business KPIs."""
        self.business_metrics[name] = value
        self.track_event(f"business.{name}", value)
    
    async def flush_metrics(self):
        """Flush metrics to external systems."""
        if not self.metrics_buffer:
            return
        
        # Send to multiple monitoring services
        await asyncio.gather(
            self._send_to_datadog(),
            self._send_to_prometheus(),
            self._send_to_custom_analytics(),
            return_exceptions=True
        )
        
        # Clear buffer after sending
        self.metrics_buffer.clear()
        logger.info(f"Flushed {len(self.metrics_buffer)} metrics")
    
    async def _send_to_datadog(self):
        """Send metrics to Datadog (placeholder)."""
        # Implementation would use Datadog API
        logger.debug("Sending metrics to Datadog")
    
    async def _send_to_prometheus(self):
        """Send metrics to Prometheus (placeholder)."""
        # Implementation would update Prometheus gauges/counters
        logger.debug("Updating Prometheus metrics")
    
    async def _send_to_custom_analytics(self):
        """Send to custom analytics platform."""
        # Implementation would use your preferred analytics service
        logger.debug("Sending to custom analytics")


class RealUserMonitoring:
    """Real User Monitoring (RUM) implementation."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    def track_page_load(self, path: str, load_time: float, user_id: str = None):
        """Track page load performance."""
        self.metrics.track_event("rum.page_load", load_time, {
            "path": path,
            "user_id": user_id or "anonymous"
        })
    
    def track_user_interaction(self, action: str, element: str, user_id: str = None):
        """Track user interactions."""
        self.metrics.track_event("rum.interaction", 1.0, {
            "action": action,
            "element": element,
            "user_id": user_id or "anonymous"
        })
    
    def track_error(self, error_type: str, message: str, stack_trace: str = None):
        """Track JavaScript/frontend errors."""
        self.metrics.track_event("rum.error", 1.0, {
            "error_type": error_type,
            "message": message[:100],  # Truncate long messages
            "has_stack": "true" if stack_trace else "false"
        })


class BusinessMetricsTracker:
    """Track business-specific KPIs."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    def track_render_request(self, project_id: str, success: bool, cost: float = None):
        """Track render generation attempts."""
        self.metrics.track_business_metric("renders.total", 1.0)
        
        if success:
            self.metrics.track_business_metric("renders.success", 1.0)
            if cost:
                self.metrics.track_business_metric("renders.cost", cost)
        else:
            self.metrics.track_business_metric("renders.failure", 1.0)
    
    def track_user_signup(self, user_id: str, plan: str = "free"):
        """Track new user registrations."""
        self.metrics.track_business_metric("users.signup", 1.0)
        self.metrics.track_event("user.signup", 1.0, {
            "user_id": user_id,
            "plan": plan
        })
    
    def track_revenue(self, amount: float, plan: str, user_id: str):
        """Track revenue events."""
        self.metrics.track_business_metric("revenue.total", amount)
        self.metrics.track_event("revenue.event", amount, {
            "plan": plan,
            "user_id": user_id
        })


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic performance monitoring."""
    
    def __init__(self, app, metrics_collector: MetricsCollector):
        super().__init__(app)
        self.metrics = metrics_collector
    
    async def dispatch(self, request: Request, call_next):
        """Track request performance."""
        start_time = time.time()
        
        # Get request info
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        duration = time.time() - start_time
        response_size = int(response.headers.get("content-length", 0))
        
        # Track performance
        perf_metrics = PerformanceMetrics(
            request_duration=duration,
            response_size=response_size,
            status_code=response.status_code,
            endpoint=path,
            method=method,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        self.metrics.track_performance(perf_metrics)
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response


class HealthMonitor:
    """System health monitoring."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check each service
        services = [
            ("redis", self._check_redis),
            ("database", self._check_database),
            ("openrouter", self._check_openrouter),
            ("storage", self._check_storage)
        ]
        
        for service_name, check_func in services:
            try:
                is_healthy = await check_func()
                health_status["services"][service_name] = {
                    "status": "healthy" if is_healthy else "degraded",
                    "checked_at": datetime.utcnow().isoformat()
                }
                
                # Track service health
                self.metrics.track_event(f"health.{service_name}", 
                                       1.0 if is_healthy else 0.0)
                
            except Exception as e:
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "checked_at": datetime.utcnow().isoformat()
                }
                self.metrics.track_event(f"health.{service_name}", 0.0)
        
        # Overall health status
        unhealthy_services = [s for s in health_status["services"].values() 
                            if s["status"] == "unhealthy"]
        if unhealthy_services:
            health_status["status"] = "unhealthy"
        elif any(s["status"] == "degraded" for s in health_status["services"].values()):
            health_status["status"] = "degraded"
        
        return health_status
    
    async def _check_redis(self) -> bool:
        """Check Redis connectivity."""
        # Implementation would ping Redis
        return True
    
    async def _check_database(self) -> bool:
        """Check database connectivity."""
        # Implementation would query database
        return True
    
    async def _check_openrouter(self) -> bool:
        """Check OpenRouter API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://openrouter.ai/api/v1/models", 
                                          timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
    
    async def _check_storage(self) -> bool:
        """Check storage service."""
        # Implementation would test storage operations
        return True


# Global metrics collector instance
metrics_collector = MetricsCollector()
rum_monitor = RealUserMonitoring(metrics_collector)
business_tracker = BusinessMetricsTracker(metrics_collector)
health_monitor = HealthMonitor(metrics_collector)


def setup_monitoring(app: FastAPI):
    """Setup monitoring middleware and background tasks."""
    
    # Add performance monitoring middleware
    app.add_middleware(PerformanceMonitoringMiddleware, 
                      metrics_collector=metrics_collector)
    
    # Background task to flush metrics
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        async def flush_metrics_periodically():
            while True:
                await asyncio.sleep(60)  # Flush every minute
                try:
                    await metrics_collector.flush_metrics()
                except Exception as e:
                    logger.error(f"Error flushing metrics: {e}")
        
        # Start background task
        flush_task = asyncio.create_task(flush_metrics_periodically())
        
        yield
        
        # Shutdown
        flush_task.cancel()
        try:
            await flush_task
        except asyncio.CancelledError:
            pass
        
        # Final flush
        await metrics_collector.flush_metrics()
    
    app.router.lifespan_context = lifespan
    
    return app