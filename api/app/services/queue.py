"""
Redis Streams-based job queue for async rendering
"""

import json
import uuid
import hashlib
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from ..core.config import settings
from ..services.langfuse import Trace

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker for external API calls"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, half_open_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout
        self.failures = 0
        self.last_failure = None
        self.state = "closed"  # closed, open, half_open
        
    def call_succeeded(self):
        """Reset failures on success"""
        self.failures = 0
        self.state = "closed"
        
    def call_failed(self):
        """Record failure and potentially open circuit"""
        self.failures += 1
        self.last_failure = datetime.utcnow()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            return True
        return False
        
    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == "closed":
            return False
            
        if self.state == "open":
            # Check if we should transition to half-open
            if self.last_failure and \
               datetime.utcnow() - self.last_failure > timedelta(seconds=self.half_open_timeout):
                self.state = "half_open"
                return False
            return True
            
        return False  # half_open allows calls


class RenderQueue:
    """Async render queue with Redis Streams"""
    
    def __init__(self):
        self.redis_url = settings.redis_url
        self.redis_client = None
        self.circuit_breaker = CircuitBreaker()
        self._connection_lock = asyncio.Lock()
        
    async def connect(self):
        """Connect to Redis with proper locking to prevent race conditions"""
        async with self._connection_lock:
            if not self.redis_client:
                try:
                    self.redis_client = await redis.from_url(
                        self.redis_url, 
                        decode_responses=True,
                        retry_on_timeout=True,
                        health_check_interval=30
                    )
                    logger.info("Redis async client connected")
                except Exception as e:
                    logger.error(f"Failed to connect to Redis: {e}")
                    raise
            
    async def enqueue_render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enqueue render job with content-based caching
        
        Args:
            payload: Render request payload
            
        Returns:
            Job info with job_id or cached result
        """
        await self.connect()
        
        # Generate content hash for caching
        content_str = json.dumps(payload, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        cache_key = f"render:{content_hash}"
        
        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            return {
                "cached": True,
                "job_id": None,
                **json.loads(cached)
            }
        
        # Generate job ID and enqueue
        job_id = str(uuid.uuid4())
        
        # Add to stream with max length limit
        await self.redis_client.xadd(
            "q:render",
            {
                "job_id": job_id,
                "payload": json.dumps(payload),
                "content_hash": content_hash,
                "created_at": datetime.utcnow().isoformat()
            },
            maxlen=10000
        )
        
        # Set initial job status
        await self.set_job_status(job_id, "queued")
        
        return {
            "cached": False,
            "job_id": job_id,
            "content_hash": content_hash
        }
        
    async def set_job_status(self, job_id: str, status: str, data: Optional[Dict] = None):
        """Update job status and publish to pubsub"""
        await self.connect()
        
        status_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if data:
            status_data.update(data)
            
        # Store status
        await self.redis_client.hset(
            f"job:{job_id}",
            mapping=status_data
        )
        
        # Publish to subscribers
        await self.redis_client.publish(
            f"job:{job_id}",
            json.dumps(status_data)
        )
        
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get current job status"""
        await self.connect()
        
        data = await self.redis_client.hgetall(f"job:{job_id}")
        if not data:
            return {"status": "not_found"}
            
        return data
        
    async def get_queue_depth(self) -> int:
        """Get current queue depth for metrics"""
        await self.connect()
        
        info = await self.redis_client.xinfo_stream("q:render")
        return info.get("length", 0)
        
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.4))
    async def call_with_breaker(self, func, *args, **kwargs):
        """Call function with circuit breaker and retry logic"""
        if self.circuit_breaker.is_open():
            raise Exception("Circuit breaker is open - using fallback")
            
        try:
            result = await func(*args, **kwargs)
            self.circuit_breaker.call_succeeded()
            return result
        except Exception as e:
            if self.circuit_breaker.call_failed():
                # Circuit opened, use fallback
                raise Exception(f"Circuit breaker opened: {e}")
            raise
            
    async def cache_render_result(self, content_hash: str, result: Dict[str, Any], ttl: int = 2592000):
        """Cache render result (30 days default)"""
        await self.connect()
        
        cache_key = f"render:{content_hash}"
        await self.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )


class RenderWorker:
    """Background worker for processing render jobs"""
    
    def __init__(self, worker_id: str = "w1", consumer_group: str = "sgd-workers"):
        self.worker_id = worker_id
        self.consumer_group = consumer_group
        self.queue = RenderQueue()
        self.running = False
        
    async def start(self):
        """Start worker loop"""
        await self.queue.connect()
        self.running = True
        
        # Create consumer group if not exists
        try:
            await self.queue.redis_client.xgroup_create("q:render", self.consumer_group, id="0")
        except:
            pass  # Group already exists
            
        while self.running:
            try:
                # Read from stream with blocking
                messages = await self.queue.redis_client.xreadgroup(
                    self.consumer_group,
                    self.worker_id,
                    {"q:render": ">"},
                    count=1,
                    block=2000
                )
                
                if not messages:
                    continue
                    
                for stream_name, stream_messages in messages:
                    for msg_id, data in stream_messages:
                        await self.process_job(msg_id, data)
                        
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(1)
                
    async def process_job(self, msg_id: str, data: Dict[str, Any]):
        """Process a single render job"""
        job_id = data.get("job_id")
        payload = json.loads(data.get("payload", "{}"))
        content_hash = data.get("content_hash")
        
        try:
            # Update status to running
            await self.queue.set_job_status(job_id, "running")
            
            # Import here to avoid circular dependency
            from ..services.openrouter import call_task
            from ..services.gemini_image import generate_images
            from ..services.storage_adapter import put_object, signed_public_url
            
            # Generate preview (lower resolution)
            preview_payload = payload.copy()
            if "outputs" in preview_payload:
                preview_payload["outputs"]["dimensions"] = "512x512"
                
            # Call with circuit breaker
            preview_result = await self.queue.call_with_breaker(
                self.generate_preview,
                preview_payload
            )
            
            # Notify preview ready
            await self.queue.set_job_status(
                job_id,
                "preview_ready",
                {"preview_url": preview_result.get("url")}
            )
            
            # Generate final image
            final_result = await self.queue.call_with_breaker(
                self.generate_final,
                payload
            )
            
            # Cache result
            await self.queue.cache_render_result(
                content_hash,
                final_result
            )
            
            # Mark complete
            await self.queue.set_job_status(
                job_id,
                "completed",
                final_result
            )
            
            # Acknowledge message
            await self.queue.redis_client.xack("q:render", self.consumer_group, msg_id)
            
        except Exception as e:
            # Mark failed
            await self.queue.set_job_status(
                job_id,
                "failed",
                {"error": str(e)}
            )
            
            # Dead letter or retry logic here
            pass
            
    async def generate_preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate low-res preview (512x512)"""
        from ..services.openrouter import call_task
        from ..services.gemini_image import generate_images
        from ..services.storage_adapter import put_object, signed_public_url
        
        # Create preview-specific payload
        preview_payload = payload.copy()
        if "outputs" in preview_payload:
            preview_payload["outputs"]["dimensions"] = "512x512"
            preview_payload["outputs"]["count"] = 1
            
        # Generate preview via Gemini
        prompt = self._make_prompt_from_payload(preview_payload)
        images = await generate_images(prompt, n=1, size="512x512")
        
        if not images:
            raise Exception("Failed to generate preview image")
            
        # Store preview image
        image_data, image_format = images[0]
        org_id = payload.get('org_id', 'anonymous')
        preview_key = f"org/{org_id}/previews/{payload['project_id']}/{uuid.uuid4()}.{image_format}"
        
        put_object(
            preview_key, 
            image_data, 
            content_type=f"image/{'jpeg' if image_format=='jpg' else image_format}"
        )
        
        preview_url = signed_public_url(preview_key, expires_seconds=30*60)  # 30 min expiry
        
        return {
            "url": preview_url,
            "r2_key": preview_key,
            "type": "preview",
            "dimensions": "512x512"
        }
        
    async def generate_final(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final high-res image"""
        from ..services.openrouter import call_task
        from ..services.gemini_image import generate_images  
        from ..services.storage_adapter import put_object, signed_public_url
        
        # Generate final image(s) at full resolution
        prompt = self._make_prompt_from_payload(payload)
        count = payload.get("outputs", {}).get("count", 1)
        dimensions = payload.get("outputs", {}).get("dimensions", "1024x1024")
        
        images = await generate_images(prompt, n=count, size=dimensions)
        
        if not images:
            raise Exception("Failed to generate final image")
            
        assets = []
        for i, (image_data, image_format) in enumerate(images):
            org_id = payload.get('org_id', 'anonymous')
            final_key = f"org/{org_id}/renders/{payload['project_id']}/{uuid.uuid4()}.{image_format}"
            
            put_object(
                final_key,
                image_data, 
                content_type=f"image/{'jpeg' if image_format=='jpg' else image_format}"
            )
            
            final_url = signed_public_url(final_key, expires_seconds=60*60)  # 1 hour expiry
            
            assets.append({
                "url": final_url,
                "r2_key": final_key,
                "synthid": {"present": False}  # SynthID not implemented yet
            })
            
        # Return single asset if only one requested, otherwise return array
        if count == 1:
            return assets[0]
        else:
            return {"assets": assets}
            
    def _make_prompt_from_payload(self, payload: Dict[str, Any]) -> str:
        """Create prompt string from job payload"""
        prompts = payload.get("prompts", {})
        constraints = payload.get("constraints", {})
        
        parts = []
        
        if prompts.get("task"):
            parts.append(f"Task: {prompts['task']}")
            
        if prompts.get("instruction"):
            parts.append(f"Instruction: {prompts['instruction']}")
            
        if constraints:
            if constraints.get("palette_hex"):
                parts.append(f"Colors: {', '.join(constraints['palette_hex'])}")
            if constraints.get("fonts"):
                parts.append(f"Fonts: {', '.join(constraints['fonts'])}")
            if constraints.get("style"):
                parts.append(f"Style: {constraints['style']}")
                
        return "\n".join(parts)
        
    async def stop(self):
        """Stop worker"""
        self.running = False


# Global queue instance
render_queue = RenderQueue()