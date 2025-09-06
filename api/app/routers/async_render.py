"""
Async render endpoints for queue-based processing
"""

from typing import Dict, Any
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from ..models.schemas import RenderRequest
from ..services.queue import render_queue
from ..services.guardrails import validate_contract
from ..services.langfuse import Trace
import json


router = APIRouter()


class AsyncRenderResponse(BaseModel):
    """Response for async render request"""
    job_id: str | None
    cached: bool
    content_hash: str | None = None
    url: str | None = None
    preview_url: str | None = None
    websocket_url: str | None = None
    

class JobStatusResponse(BaseModel):
    """Job status response"""
    status: str
    job_id: str | None = None
    progress: int | None = None
    preview_url: str | None = None
    url: str | None = None
    r2_key: str | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    synthid: Dict[str, Any] | None = None


@router.post("/render/async", response_model=AsyncRenderResponse)
async def async_render(request: RenderRequest = Body(...)):
    """
    Async render endpoint that uses Redis queue for processing.
    
    For complex renders or when you need real-time updates,
    this endpoint queues the job and returns immediately.
    
    Flow:
    1. Validate request and apply content filters
    2. Check for cached result based on content hash
    3. If not cached, enqueue job in Redis Stream
    4. Return job_id and WebSocket URL for status updates
    5. Background worker processes the job
    6. Client can poll /render/jobs/{job_id} or use WebSocket
    """
    trace = Trace("async_render")
    
    # Apply same validation as sync render
    from .render import _content_filter, _validate_references, _make_planner_prompt
    
    _content_filter(request.prompts.instruction)
    _validate_references(getattr(request.prompts, "references", None))
    
    # Create payload for queue
    payload = {
        "project_id": request.project_id,
        "prompts": request.prompts.model_dump(),
        "outputs": request.outputs.model_dump(),
        "constraints": request.constraints.model_dump() if request.constraints else None,
        "trace_id": trace.id
    }
    
    try:
        # Enqueue the render job
        result = await render_queue.enqueue_render(payload)
        
        if result["cached"]:
            # Return cached result immediately
            return AsyncRenderResponse(
                job_id=None,
                cached=True,
                url=result.get("url"),
                content_hash=result.get("content_hash")
            )
        else:
            # Return job info for tracking
            job_id = result["job_id"]
            return AsyncRenderResponse(
                job_id=job_id,
                cached=False,
                content_hash=result.get("content_hash"),
                websocket_url=f"/ws/jobs/{job_id}"
            )
            
    except Exception as e:
        await trace.flush()
        raise HTTPException(status_code=502, detail={"queue": str(e)})
    
    await trace.flush()


@router.get("/render/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get current status of an async render job.
    
    Status values:
    - queued: Job is in queue waiting to be processed
    - running: Job is being processed
    - preview_ready: Low-res preview is available
    - completed: Final high-res image is ready
    - failed: Job failed with error
    - not_found: Job ID not found
    """
    try:
        status = await render_queue.get_job_status(job_id)
        
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Job not found")
            
        return JobStatusResponse(
            job_id=job_id,
            status=status.get("status", "unknown"),
            preview_url=status.get("preview_url"),
            url=status.get("url"),
            r2_key=status.get("r2_key"),
            error=status.get("error"),
            created_at=status.get("created_at"),
            updated_at=status.get("updated_at"),
            synthid=status.get("synthid"),
            progress=status.get("progress", 0 if status.get("status") == "queued" else 50 if status.get("status") == "preview_ready" else 100 if status.get("status") == "completed" else None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": str(e)})


@router.get("/render/queue/stats")
async def get_queue_stats():
    """
    Get queue statistics for monitoring and dashboard.
    
    Returns current queue depth and processing metrics.
    """
    try:
        depth = await render_queue.get_queue_depth()
        
        # Additional metrics could be added here
        return {
            "queue_depth": depth,
            "status": "healthy" if depth < 100 else "busy",
            "estimated_wait_minutes": min(depth * 2, 30)  # Rough estimate
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"queue_stats": str(e)})


@router.delete("/render/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a queued or running job.
    
    Note: Jobs that are already being processed may not be
    immediately cancelled depending on the processing stage.
    """
    try:
        status = await render_queue.get_job_status(job_id)
        
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Job not found")
            
        if status.get("status") in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or failed job")
            
        # Mark job as cancelled
        await render_queue.set_job_status(job_id, "cancelled")
        
        return {"message": "Job cancelled successfully", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"cancel": str(e)})