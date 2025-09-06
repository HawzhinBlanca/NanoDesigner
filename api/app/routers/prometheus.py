"""
Prometheus metrics endpoint for monitoring and observability
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Response
from collections import Counter, defaultdict
import asyncio

from ..services.queue import render_queue
from ..services.redis import get_client as get_redis_client


router = APIRouter()

# Global metrics storage
_metrics = {
    "api_requests_total": Counter(),
    "api_request_duration_seconds": defaultdict(list),
    "render_jobs_total": Counter(),
    "render_job_duration_seconds": defaultdict(list),
    "redis_operations_total": Counter(),
    "qdrant_operations_total": Counter(),
    "queue_depth_current": 0,
    "active_websocket_connections": 0,
    "start_time": time.time()
}

# Metric labels
REQUEST_LABELS = ["method", "endpoint", "status_code"]
JOB_LABELS = ["status", "project_id", "output_format"]


def track_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track API request metrics"""
    labels = f'{method}_{endpoint}_{status_code}'.replace('/', '_').replace('-', '_')
    _metrics["api_requests_total"][labels] += 1
    _metrics["api_request_duration_seconds"][labels].append(duration)


def track_job(status: str, project_id: str, output_format: str, duration: float = None):
    """Track render job metrics"""
    labels = f'{status}_{project_id}_{output_format}'.replace('/', '_').replace('-', '_')
    _metrics["render_jobs_total"][labels] += 1
    if duration:
        _metrics["render_job_duration_seconds"][labels].append(duration)


def track_redis_operation(operation: str):
    """Track Redis operation metrics"""
    _metrics["redis_operations_total"][operation] += 1


def track_qdrant_operation(operation: str):
    """Track Qdrant operation metrics"""
    _metrics["qdrant_operations_total"][operation] += 1


def update_websocket_connections(count: int):
    """Update active WebSocket connection count"""
    _metrics["active_websocket_connections"] = count


async def update_queue_metrics():
    """Update queue-related metrics"""
    try:
        depth = await render_queue.get_queue_depth()
        _metrics["queue_depth_current"] = depth
    except:
        pass


def format_prometheus_metrics() -> str:
    """Format metrics in Prometheus exposition format"""
    lines = []
    
    # API Request metrics
    lines.append("# HELP api_requests_total Total number of API requests")
    lines.append("# TYPE api_requests_total counter")
    for labels, count in _metrics["api_requests_total"].items():
        method, endpoint, status = labels.split('_', 2)
        lines.append(f'api_requests_total{{method="{method}",endpoint="{endpoint}",status_code="{status}"}} {count}')
    
    # API Request duration
    lines.append("# HELP api_request_duration_seconds API request duration in seconds")
    lines.append("# TYPE api_request_duration_seconds histogram")
    for labels, durations in _metrics["api_request_duration_seconds"].items():
        if durations:
            method, endpoint, status = labels.split('_', 2)
            avg_duration = sum(durations) / len(durations)
            lines.append(f'api_request_duration_seconds{{method="{method}",endpoint="{endpoint}",status_code="{status}"}} {avg_duration:.4f}')
    
    # Render job metrics
    lines.append("# HELP render_jobs_total Total number of render jobs")
    lines.append("# TYPE render_jobs_total counter")
    for labels, count in _metrics["render_jobs_total"].items():
        status, project_id, output_format = labels.split('_', 2)
        lines.append(f'render_jobs_total{{status="{status}",project_id="{project_id}",output_format="{output_format}"}} {count}')
    
    # Queue depth
    lines.append("# HELP queue_depth_current Current number of jobs in render queue")
    lines.append("# TYPE queue_depth_current gauge")
    lines.append(f"queue_depth_current {_metrics['queue_depth_current']}")
    
    # WebSocket connections
    lines.append("# HELP websocket_connections_active Current number of active WebSocket connections")
    lines.append("# TYPE websocket_connections_active gauge")
    lines.append(f"websocket_connections_active {_metrics['active_websocket_connections']}")
    
    # Redis operations
    lines.append("# HELP redis_operations_total Total number of Redis operations")
    lines.append("# TYPE redis_operations_total counter")
    for operation, count in _metrics["redis_operations_total"].items():
        lines.append(f'redis_operations_total{{operation="{operation}"}} {count}')
    
    # Qdrant operations
    lines.append("# HELP qdrant_operations_total Total number of Qdrant operations")
    lines.append("# TYPE qdrant_operations_total counter")
    for operation, count in _metrics["qdrant_operations_total"].items():
        lines.append(f'qdrant_operations_total{{operation="{operation}"}} {count}')
    
    # Application uptime
    uptime = time.time() - _metrics["start_time"]
    lines.append("# HELP application_uptime_seconds Application uptime in seconds")
    lines.append("# TYPE application_uptime_seconds counter")
    lines.append(f"application_uptime_seconds {uptime:.2f}")
    
    # Python process metrics
    import psutil
    import os
    process = psutil.Process(os.getpid())
    
    lines.append("# HELP process_cpu_percent Current CPU usage percentage")
    lines.append("# TYPE process_cpu_percent gauge")
    lines.append(f"process_cpu_percent {process.cpu_percent()}")
    
    lines.append("# HELP process_memory_bytes Current memory usage in bytes")
    lines.append("# TYPE process_memory_bytes gauge")
    lines.append(f"process_memory_bytes {process.memory_info().rss}")
    
    lines.append("# HELP process_open_fds Current number of open file descriptors")
    lines.append("# TYPE process_open_fds gauge")
    lines.append(f"process_open_fds {process.num_fds()}")
    
    return "\n".join(lines) + "\n"


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint in exposition format.
    
    This endpoint provides comprehensive metrics about the application:
    - API request counts and durations by endpoint and status
    - Render job statistics by status and format
    - Queue depth and processing metrics
    - Active WebSocket connections
    - Redis and Qdrant operation counts
    - System resource usage (CPU, memory, file descriptors)
    
    Compatible with Prometheus scraping and Grafana dashboards.
    """
    # Update dynamic metrics
    await update_queue_metrics()
    
    metrics_text = format_prometheus_metrics()
    
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get("/metrics/health")
async def metrics_health():
    """
    Health endpoint specifically for metrics collection.
    
    Returns condensed health status for monitoring systems.
    """
    await update_queue_metrics()
    
    return {
        "status": "healthy",
        "uptime_seconds": time.time() - _metrics["start_time"],
        "queue_depth": _metrics["queue_depth_current"],
        "active_connections": _metrics["active_websocket_connections"],
        "total_requests": sum(_metrics["api_requests_total"].values()),
        "total_jobs": sum(_metrics["render_jobs_total"].values())
    }