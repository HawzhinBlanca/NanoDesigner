"""
Admin endpoints for worker and system management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..services.worker_manager import worker_manager
from ..services.queue import render_queue


router = APIRouter()


class ScaleWorkersRequest(BaseModel):
    """Request to scale workers"""
    target_count: int
    

class WorkerActionResponse(BaseModel):
    """Response for worker actions"""
    success: bool
    message: str
    worker_id: Optional[str] = None
    

@router.get("/admin/workers")
async def get_worker_stats():
    """
    Get comprehensive worker statistics.
    
    Returns information about all workers including:
    - Total, running, and stopped worker counts
    - Individual worker status and job counts
    - Overall system health
    """
    try:
        stats = worker_manager.get_worker_stats()
        health = await worker_manager.health_check()
        
        return {
            **stats,
            "health": health
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker stats: {e}")


@router.post("/admin/workers/start", response_model=WorkerActionResponse)
async def start_worker(worker_id: Optional[str] = None):
    """
    Start a new render worker.
    
    If worker_id is not provided, a unique ID will be generated.
    """
    try:
        created_worker_id = await worker_manager.start_worker(worker_id)
        
        return WorkerActionResponse(
            success=True,
            message=f"Worker started successfully",
            worker_id=created_worker_id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start worker: {e}")


@router.delete("/admin/workers/{worker_id}", response_model=WorkerActionResponse)
async def stop_worker(worker_id: str):
    """
    Stop a specific render worker.
    
    The worker will finish its current job before stopping.
    """
    try:
        success = await worker_manager.stop_worker(worker_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Worker not found")
            
        return WorkerActionResponse(
            success=True,
            message=f"Worker stopped successfully",
            worker_id=worker_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop worker: {e}")


@router.post("/admin/workers/{worker_id}/restart", response_model=WorkerActionResponse)
async def restart_worker(worker_id: str):
    """
    Restart a specific render worker.
    
    This will stop the worker and start a new one with the same ID.
    """
    try:
        success = await worker_manager.restart_worker(worker_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Worker not found")
            
        return WorkerActionResponse(
            success=True,
            message=f"Worker restarted successfully",
            worker_id=worker_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart worker: {e}")


@router.post("/admin/workers/scale")
async def scale_workers(request: ScaleWorkersRequest):
    """
    Scale workers to the target count.
    
    Will start or stop workers as needed to reach the target.
    Maximum workers is limited by MAX_RENDER_WORKERS environment variable.
    """
    try:
        result = await worker_manager.scale_workers(request.target_count)
        
        return {
            "success": True,
            "message": f"Scaled to {result['current_count']} workers",
            **result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scale workers: {e}")


@router.post("/admin/workers/autoscale")
async def trigger_autoscale():
    """
    Trigger auto-scaling based on current queue depth.
    
    This endpoint can be called by external monitoring systems
    or scheduled tasks to automatically adjust worker count.
    """
    try:
        queue_depth = await render_queue.get_queue_depth()
        result = await worker_manager.auto_scale(queue_depth)
        
        return {
            "success": True,
            "message": f"Auto-scaled based on queue depth ({queue_depth} jobs)",
            "queue_depth": queue_depth,
            **result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-scaling failed: {e}")


@router.get("/admin/system")
async def get_system_stats():
    """
    Get comprehensive system statistics.
    
    Includes queue status, worker health, and resource usage.
    """
    try:
        # Queue stats
        queue_depth = await render_queue.get_queue_depth()
        
        # Worker stats  
        worker_stats = worker_manager.get_worker_stats()
        worker_health = await worker_manager.health_check()
        
        # System metrics
        import psutil
        import os
        process = psutil.Process(os.getpid())
        
        return {
            "queue": {
                "depth": queue_depth,
                "status": "healthy" if queue_depth < 100 else "busy"
            },
            "workers": {
                **worker_stats,
                "health": worker_health
            },
            "system": {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss // 1024 // 1024,
                "open_files": process.num_fds(),
                "pid": os.getpid()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {e}")


@router.post("/admin/system/clear-cache")
async def clear_redis_cache():
    """
    Clear Redis cache (use with caution in production).
    
    This will clear all cached render results and embeddings.
    """
    try:
        import redis.asyncio as redis
        from ..core.config import settings
        
        redis_client = await redis.from_url(settings.redis_url)
        
        # Get cache key patterns
        cache_keys = await redis_client.keys("render:*")
        cache_keys.extend(await redis_client.keys("embed:*"))
        cache_keys.extend(await redis_client.keys("plan:*"))
        
        if cache_keys:
            deleted = await redis_client.delete(*cache_keys)
        else:
            deleted = 0
            
        await redis_client.close()
        
        return {
            "success": True,
            "message": f"Cleared {deleted} cache keys",
            "deleted_keys": deleted
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")