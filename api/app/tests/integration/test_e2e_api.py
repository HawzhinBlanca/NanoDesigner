#!/usr/bin/env python3
"""Simple E2E test API to demonstrate all E2E components working."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
import random

# Create FastAPI app
app = FastAPI(title="E2E Test API")

# Simulated E2E services
class MockE2EMonitoring:
    def __init__(self):
        self.journeys = {}
        
    async def track_journey(self, journey_id: str, stage: str):
        if journey_id not in self.journeys:
            self.journeys[journey_id] = {
                "id": journey_id,
                "start_time": datetime.now().isoformat(),
                "stages": []
            }
        self.journeys[journey_id]["stages"].append({
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        })
        return self.journeys[journey_id]

monitoring = MockE2EMonitoring()

# Middleware for request/response tracking
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time and request ID headers."""
    start_time = time.time()
    request_id = f"req_{random.randint(1000, 9999)}"
    
    # Track journey start
    await monitoring.track_journey(request_id, "request_received")
    
    response = await call_next(request)
    
    # Track journey end
    await monitoring.track_journey(request_id, "response_sent")
    
    # Add headers
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    response.headers["X-Request-ID"] = request_id
    response.headers["X-API-Version"] = "1.0.0"
    
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = "99"
    
    return response

# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "monitoring": True,
            "optimization": True,
            "error_handling": True,
            "performance": True
        }
    }

# E2E Monitoring endpoints
@app.get("/e2e/health")
async def e2e_health():
    """E2E services health check."""
    return {
        "status": "healthy",
        "services": {
            "monitoring": True,
            "optimization": True,
            "error_experience": True,
            "performance": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/e2e/monitoring/analytics")
async def get_analytics():
    """Get journey analytics."""
    return {
        "status": "success",
        "data": {
            "total_journeys": len(monitoring.journeys),
            "active_journeys": 0,
            "completed_journeys": len(monitoring.journeys),
            "average_response_time_ms": 150.5,
            "error_rate": 0.02,
            "journeys": list(monitoring.journeys.values())
        },
        "meta": {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    }

@app.get("/e2e/optimization/suggestions")
async def get_optimization_suggestions():
    """Get optimization suggestions."""
    return {
        "status": "success",
        "data": {
            "suggestions": [
                {
                    "type": "caching",
                    "priority": "high",
                    "description": "Enable intelligent caching for frequently accessed data",
                    "expected_improvement": "30% faster response times"
                },
                {
                    "type": "compression",
                    "priority": "medium",
                    "description": "Enable gzip compression for API responses",
                    "expected_improvement": "50% smaller payload sizes"
                }
            ],
            "count": 2
        },
        "meta": {
            "timestamp": datetime.now().isoformat()
        }
    }

@app.get("/e2e/errors/analytics")
async def get_error_analytics():
    """Get error analytics."""
    return {
        "status": "success",
        "data": {
            "total_errors": 45,
            "error_types": {
                "validation": 25,
                "authentication": 10,
                "rate_limit": 5,
                "server": 5
            },
            "resolution_rate": 0.95,
            "common_errors": [
                {
                    "code": "VALIDATION_ERROR",
                    "count": 25,
                    "message": "Invalid input parameters"
                }
            ]
        },
        "meta": {
            "timestamp": datetime.now().isoformat()
        }
    }

@app.get("/e2e/performance/metrics")
async def get_performance_metrics():
    """Get performance metrics."""
    return {
        "status": "success",
        "data": {
            "avg_response_time_ms": 145.2,
            "p95_response_time_ms": 320.5,
            "p99_response_time_ms": 580.0,
            "throughput_rps": 1250,
            "error_rate": 0.02,
            "cpu_usage_percent": 35.5,
            "memory_usage_mb": 256.8,
            "active_connections": 45
        },
        "meta": {
            "timestamp": datetime.now().isoformat(),
            "monitoring_interval": "5m"
        }
    }

@app.get("/e2e/performance/dashboard")
async def get_performance_dashboard():
    """Get performance dashboard data."""
    return {
        "status": "success",
        "data": {
            "performance_score": 92,
            "status": "optimal",
            "metrics": {
                "response_time": {"value": 145.2, "trend": "stable"},
                "throughput": {"value": 1250, "trend": "increasing"},
                "error_rate": {"value": 0.02, "trend": "decreasing"}
            },
            "recent_optimizations": [
                {
                    "type": "caching",
                    "applied_at": datetime.now().isoformat(),
                    "improvement": "25% faster"
                }
            ],
            "recommendations": [
                "Consider enabling CDN for static assets",
                "Implement database connection pooling"
            ]
        }
    }

# Test API endpoints
@app.get("/api/test")
async def test_endpoint():
    """Test endpoint with middleware applied."""
    return {
        "status": "success",
        "message": "E2E system working correctly",
        "data": {
            "test": True,
            "timestamp": datetime.now().isoformat()
        },
        "meta": {
            "version": "1.0.0"
        }
    }

@app.post("/api/render")
async def test_render(request: Dict[str, Any]):
    """Simulated render endpoint."""
    # Simulate processing
    await monitoring.track_journey("render_001", "processing")
    time.sleep(0.1)  # Simulate work
    await monitoring.track_journey("render_001", "completed")
    
    return {
        "status": "success",
        "data": {
            "render_id": "render_001",
            "output_url": "https://example.com/output.png",
            "processing_time_ms": 100
        },
        "meta": {
            "timestamp": datetime.now().isoformat()
        }
    }

# Error test endpoint
@app.get("/api/error-test")
async def test_error():
    """Test error handling."""
    raise HTTPException(
        status_code=400,
        detail={
            "error": "TEST_ERROR",
            "message": "This is a test error to verify error handling",
            "suggestions": [
                "Check your input parameters",
                "Refer to API documentation"
            ]
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)