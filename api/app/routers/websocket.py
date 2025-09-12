"""
WebSocket endpoints for real-time job status updates
"""

from typing import Dict, Any, Optional
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from ..core.config import settings
from ..services.langfuse import Trace


router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for job updates (per-connection pubsub)."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis_client: Optional[redis.Redis] = None
        self._job_pubsubs: Dict[str, Any] = {}
        
    async def connect(self, job_id: str, websocket: WebSocket):
        """Accept connection and start listening to Redis pub/sub"""
        await websocket.accept()
        self.active_connections[job_id] = websocket
        
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.redis_url, decode_responses=True)
        # Create dedicated pubsub for this job
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"job:{job_id}")
        self._job_pubsubs[job_id] = pubsub
        
    async def disconnect(self, job_id: str):
        """Remove connection and unsubscribe"""
        if job_id in self.active_connections:
            del self.active_connections[job_id]
        pubsub = self._job_pubsubs.pop(job_id, None)
        if pubsub:
            try:
                await pubsub.unsubscribe(f"job:{job_id}")
                await pubsub.aclose()
            except Exception:
                pass
            
    async def send_update(self, job_id: str, message: Dict[str, Any]):
        """Send message to specific connection"""
        if job_id in self.active_connections:
            websocket = self.active_connections[job_id]
            await websocket.send_json(message)
            
    async def listen_for_updates(self, job_id: str):
        """Listen for Redis pub/sub messages and forward to WebSocket"""
        pubsub = self._job_pubsubs.get(job_id)
        if not pubsub:
            return
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self.send_update(job_id, data)
                    if data.get("status") in ["completed", "failed", "cancelled"]:
                        await self.disconnect(job_id)
                        break
        except Exception as e:
            print(f"Error in WebSocket listener: {e}")
            

manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job status updates.
    
    Client connects to this endpoint to receive real-time updates
    about their render job status via Redis pub/sub.
    
    Example client code:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);
    ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        console.log('Job update:', update);
        
        if (update.status === 'preview_ready') {
            // Show preview image
            showPreview(update.preview_url);
        } else if (update.status === 'completed') {
            // Show final result
            showFinal(update.url);
        }
    };
    ```
    """
    trace = Trace("websocket_job")
    
    try:
        await manager.connect(job_id, websocket)
        
        # Send initial status
        redis_client = await redis.from_url(settings.redis_url, decode_responses=True)
        status = await redis_client.hgetall(f"job:{job_id}")
        if status:
            await manager.send_update(job_id, status)
            
        # Listen for updates
        await manager.listen_for_updates(job_id)
        
    except WebSocketDisconnect:
        await manager.disconnect(job_id)
    except Exception as e:
        trace.log(f"WebSocket error: {e}")
        await manager.disconnect(job_id)
    finally:
        await trace.flush()


@router.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    """Health check WebSocket endpoint for monitoring"""
    await websocket.accept()
    
    try:
        while True:
            # Send ping every 30 seconds
            await websocket.send_json({"type": "ping", "timestamp": asyncio.get_event_loop().time()})
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass