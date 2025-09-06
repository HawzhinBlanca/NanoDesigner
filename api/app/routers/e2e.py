"""End-to-end monitoring and optimization endpoints."""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from ..services.e2e_monitoring import E2EMonitoringService
from ..services.journey_optimizer import JourneyOptimizer
from ..services.error_experience import ErrorExperienceService
from ..services.e2e_performance import E2EPerformanceOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/e2e", tags=["E2E Monitoring"])

# Service instances (will be injected from main.py)
e2e_monitoring: Optional[E2EMonitoringService] = None
journey_optimizer: Optional[JourneyOptimizer] = None
error_experience: Optional[ErrorExperienceService] = None
performance_optimizer: Optional[E2EPerformanceOptimizer] = None

def set_e2e_services(
    monitoring: E2EMonitoringService,
    optimizer: JourneyOptimizer,
    error_exp: ErrorExperienceService,
    perf_opt: E2EPerformanceOptimizer
):
    """Set E2E service instances."""
    global e2e_monitoring, journey_optimizer, error_experience, performance_optimizer
    e2e_monitoring = monitoring
    journey_optimizer = optimizer
    error_experience = error_exp
    performance_optimizer = perf_opt

@router.get("/monitoring/journey/{journey_id}")
async def get_journey_details(journey_id: str):
    """Get detailed information about a specific journey."""
    if not e2e_monitoring:
        raise HTTPException(status_code=503, detail="E2E monitoring not available")
    
    try:
        journey_data = await e2e_monitoring.get_journey_details(journey_id)
        if not journey_data:
            raise HTTPException(status_code=404, detail="Journey not found")
        
        return {
            "status": "success",
            "data": journey_data
        }
    except Exception as e:
        logger.error(f"Error getting journey details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve journey details")

@router.get("/monitoring/analytics")
async def get_journey_analytics(
    hours_back: int = Query(24, description="Hours of data to analyze"),
    journey_type: Optional[str] = Query(None, description="Filter by journey type")
):
    """Get journey analytics and insights."""
    if not e2e_monitoring:
        raise HTTPException(status_code=503, detail="E2E monitoring not available")
    
    try:
        since = datetime.now() - timedelta(hours=hours_back)
        analytics = await e2e_monitoring.get_journey_analytics(
            since=since,
            journey_type=journey_type
        )
        
        return {
            "status": "success",
            "data": analytics,
            "meta": {
                "time_range": f"Last {hours_back} hours",
                "journey_type": journey_type
            }
        }
    except Exception as e:
        logger.error(f"Error getting journey analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

@router.get("/optimization/suggestions")
async def get_optimization_suggestions(
    user_id: Optional[str] = Query(None, description="User ID for personalized suggestions"),
    limit: int = Query(10, description="Maximum number of suggestions")
):
    """Get optimization suggestions for improving user experience."""
    if not journey_optimizer:
        raise HTTPException(status_code=503, detail="Journey optimizer not available")
    
    try:
        suggestions = await journey_optimizer.get_optimization_suggestions(
            user_id=user_id,
            limit=limit
        )
        
        return {
            "status": "success",
            "data": {
                "suggestions": suggestions,
                "count": len(suggestions)
            }
        }
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve suggestions")

@router.post("/optimization/apply")
async def apply_optimization(
    optimization_data: Dict[str, Any]
):
    """Apply a specific optimization."""
    if not journey_optimizer:
        raise HTTPException(status_code=503, detail="Journey optimizer not available")
    
    try:
        result = await journey_optimizer.apply_optimization(optimization_data)
        
        return {
            "status": "success",
            "data": result,
            "message": "Optimization applied successfully"
        }
    except Exception as e:
        logger.error(f"Error applying optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply optimization")

@router.get("/errors/experience/{error_code}")
async def get_error_experience(error_code: str):
    """Get enhanced error experience for a specific error code."""
    if not error_experience:
        raise HTTPException(status_code=503, detail="Error experience service not available")
    
    try:
        experience = await error_experience.get_error_experience(error_code)
        
        if not experience:
            raise HTTPException(status_code=404, detail="Error code not found")
        
        return {
            "status": "success",
            "data": experience
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting error experience: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error experience")

@router.get("/errors/analytics")
async def get_error_analytics(
    hours_back: int = Query(24, description="Hours of data to analyze"),
    error_type: Optional[str] = Query(None, description="Filter by error type")
):
    """Get error analytics and patterns."""
    if not error_experience:
        raise HTTPException(status_code=503, detail="Error experience service not available")
    
    try:
        since = datetime.now() - timedelta(hours=hours_back)
        analytics = await error_experience.get_error_analytics(
            since=since,
            error_type=error_type
        )
        
        return {
            "status": "success",
            "data": analytics,
            "meta": {
                "time_range": f"Last {hours_back} hours",
                "error_type": error_type
            }
        }
    except Exception as e:
        logger.error(f"Error getting error analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error analytics")

@router.get("/performance/metrics")
async def get_performance_metrics(
    hours_back: int = Query(24, description="Hours of data to analyze")
):
    """Get performance metrics and optimization status."""
    if not performance_optimizer:
        raise HTTPException(status_code=503, detail="Performance optimizer not available")
    
    try:
        since = datetime.now() - timedelta(hours=hours_back)
        metrics = await performance_optimizer.get_performance_metrics(since=since)
        
        return {
            "status": "success",
            "data": metrics,
            "meta": {
                "time_range": f"Last {hours_back} hours"
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")

@router.post("/performance/optimize")
async def trigger_performance_optimization(
    optimization_type: str = Query(..., description="Type of optimization to apply"),
    force: bool = Query(False, description="Force optimization even if not needed")
):
    """Trigger performance optimization."""
    if not performance_optimizer:
        raise HTTPException(status_code=503, detail="Performance optimizer not available")
    
    try:
        result = await performance_optimizer.optimize_performance(
            optimization_type=optimization_type,
            force=force
        )
        
        return {
            "status": "success",
            "data": result,
            "message": f"Performance optimization '{optimization_type}' completed"
        }
    except Exception as e:
        logger.error(f"Error triggering performance optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger optimization")

@router.get("/performance/dashboard")
async def get_performance_dashboard():
    """Get performance dashboard data."""
    if not performance_optimizer:
        raise HTTPException(status_code=503, detail="Performance optimizer not available")
    
    try:
        dashboard_data = await performance_optimizer.get_dashboard_data()
        
        return {
            "status": "success",
            "data": dashboard_data
        }
    except Exception as e:
        logger.error(f"Error getting performance dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")

@router.get("/health")
async def get_e2e_health():
    """Check health status of all E2E services."""
    health_status = {
        "monitoring": e2e_monitoring is not None,
        "optimization": journey_optimizer is not None,
        "error_experience": error_experience is not None,
        "performance": performance_optimizer is not None
    }
    
    all_healthy = all(health_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": health_status,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status")
async def get_e2e_status():
    """Get detailed status of all E2E services."""
    status_data = {}
    
    if e2e_monitoring:
        try:
            status_data["monitoring"] = await e2e_monitoring.get_status()
        except Exception as e:
            status_data["monitoring"] = {"status": "error", "error": str(e)}
    
    if journey_optimizer:
        try:
            status_data["optimization"] = await journey_optimizer.get_status()
        except Exception as e:
            status_data["optimization"] = {"status": "error", "error": str(e)}
    
    if error_experience:
        try:
            status_data["error_experience"] = await error_experience.get_status()
        except Exception as e:
            status_data["error_experience"] = {"status": "error", "error": str(e)}
    
    if performance_optimizer:
        try:
            status_data["performance"] = await performance_optimizer.get_status()
        except Exception as e:
            status_data["performance"] = {"status": "error", "error": str(e)}
    
    return {
        "status": "success",
        "data": status_data,
        "timestamp": datetime.now().isoformat()
    }