"""
Production monitoring endpoints for NanoDesigner.
Provides health checks, metrics, and observability endpoints.
"""

from __future__ import annotations

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..monitoring.production_monitoring import (
    metrics_collector,
    rum_monitor, 
    business_tracker,
    health_monitor
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    responses={
        503: {"description": "Service Unavailable"}
    }
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    services: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Metrics response model."""
    performance: Dict[str, Any]
    business: Dict[str, Any]
    system: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive system health check.
    
    Returns the health status of all critical services:
    - Redis (caching)
    - Database (persistence)  
    - OpenRouter (AI services)
    - Storage (file storage)
    
    Status levels:
    - healthy: All services operational
    - degraded: Some services have issues but core functionality works
    - unhealthy: Critical services down, system not operational
    """
    try:
        health_data = await health_monitor.check_system_health()
        
        # Return appropriate HTTP status
        if health_data["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail="System unhealthy")
        elif health_data["status"] == "degraded":
            # Return 200 but log warning
            logger.warning("System health degraded")
        
        return HealthResponse(**health_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Health check failed")


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    Simple check to verify the service is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    Checks if service is ready to handle requests.
    """
    try:
        # Quick health check of critical services
        health_data = await health_monitor.check_system_health()
        
        if health_data["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return {
            "status": "ready", 
            "timestamp": datetime.utcnow().isoformat(),
            "services": health_data["status"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Readiness check failed")


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    hours: int = Query(default=1, ge=1, le=24, description="Hours of metrics to return")
):
    """
    Get system metrics for monitoring dashboards.
    
    Returns performance, business, and system metrics for the specified time period.
    Used by monitoring dashboards and alerting systems.
    """
    try:
        # Calculate performance metrics
        recent_perf = metrics_collector.performance_metrics[-1000:]  # Last 1000 requests
        
        if recent_perf:
            avg_duration = sum(p.request_duration for p in recent_perf) / len(recent_perf)
            p95_duration = sorted([p.request_duration for p in recent_perf])[int(len(recent_perf) * 0.95)]
            error_rate = len([p for p in recent_perf if p.status_code >= 400]) / len(recent_perf)
        else:
            avg_duration = p95_duration = error_rate = 0.0
        
        performance_metrics = {
            "request_count": len(recent_perf),
            "avg_response_time": round(avg_duration, 3),
            "p95_response_time": round(p95_duration, 3),
            "error_rate": round(error_rate * 100, 2),
            "status_codes": self._get_status_code_distribution(recent_perf)
        }
        
        # Business metrics
        business_metrics = {
            "renders_total": metrics_collector.business_metrics.get("renders.total", 0),
            "renders_success": metrics_collector.business_metrics.get("renders.success", 0),
            "renders_failure": metrics_collector.business_metrics.get("renders.failure", 0),
            "revenue_total": metrics_collector.business_metrics.get("revenue.total", 0.0),
            "users_signup": metrics_collector.business_metrics.get("users.signup", 0)
        }
        
        # System metrics
        system_metrics = {
            "uptime_hours": hours,  # Placeholder - would calculate actual uptime
            "memory_usage_mb": 0,   # Would get actual memory usage
            "cpu_usage_percent": 0, # Would get actual CPU usage
            "disk_usage_percent": 0 # Would get actual disk usage
        }
        
        return MetricsResponse(
            performance=performance_metrics,
            business=business_metrics,
            system=system_metrics
        )
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.post("/metrics/track")
async def track_custom_metric(
    name: str,
    value: float = 1.0,
    tags: Dict[str, str] = None
):
    """
    Track custom metric event.
    
    Allows applications to send custom business metrics.
    """
    try:
        metrics_collector.track_event(name, value, tags or {})
        return {"status": "tracked", "metric": name, "value": value}
    except Exception as e:
        logger.error(f"Error tracking metric {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to track metric")


@router.post("/rum/track")
async def track_rum_event(
    event_type: str,
    data: Dict[str, Any]
):
    """
    Track Real User Monitoring (RUM) event.
    
    Receives frontend performance and error data.
    """
    try:
        if event_type == "page_load":
            rum_monitor.track_page_load(
                path=data.get("path", "/"),
                load_time=data.get("load_time", 0.0),
                user_id=data.get("user_id")
            )
        elif event_type == "interaction":
            rum_monitor.track_user_interaction(
                action=data.get("action", "unknown"),
                element=data.get("element", "unknown"),
                user_id=data.get("user_id")
            )
        elif event_type == "error":
            rum_monitor.track_error(
                error_type=data.get("error_type", "unknown"),
                message=data.get("message", ""),
                stack_trace=data.get("stack_trace")
            )
        else:
            raise ValueError(f"Unknown event type: {event_type}")
        
        return {"status": "tracked", "event_type": event_type}
        
    except Exception as e:
        logger.error(f"Error tracking RUM event {event_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to track RUM event")


@router.get("/alerts")
async def get_active_alerts():
    """
    Get active system alerts.
    
    Returns current alerts that require attention.
    """
    try:
        alerts = []
        
        # Check recent performance
        recent_perf = metrics_collector.performance_metrics[-100:]  # Last 100 requests
        if recent_perf:
            avg_duration = sum(p.request_duration for p in recent_perf) / len(recent_perf)
            error_rate = len([p for p in recent_perf if p.status_code >= 500]) / len(recent_perf)
            
            # Performance alerts
            if avg_duration > 2.0:  # > 2 seconds average
                alerts.append({
                    "level": "warning",
                    "message": f"High response time: {avg_duration:.2f}s average",
                    "metric": "response_time",
                    "value": avg_duration
                })
            
            if error_rate > 0.05:  # > 5% error rate
                alerts.append({
                    "level": "critical", 
                    "message": f"High error rate: {error_rate*100:.1f}%",
                    "metric": "error_rate",
                    "value": error_rate
                })
        
        # Business metric alerts
        render_success_rate = (
            metrics_collector.business_metrics.get("renders.success", 0) /
            max(metrics_collector.business_metrics.get("renders.total", 1), 1)
        )
        
        if render_success_rate < 0.95:  # < 95% success rate
            alerts.append({
                "level": "warning",
                "message": f"Low render success rate: {render_success_rate*100:.1f}%",
                "metric": "render_success_rate", 
                "value": render_success_rate
            })
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


def _get_status_code_distribution(perf_metrics):
    """Calculate status code distribution."""
    if not perf_metrics:
        return {}
    
    distribution = {}
    for perf in perf_metrics:
        code = perf.status_code
        distribution[code] = distribution.get(code, 0) + 1
    
    return distribution