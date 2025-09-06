"""
Worker process management for async render queue
"""

import asyncio
import uuid
from typing import Dict, List, Optional
from datetime import datetime
import signal
import os

from .queue import RenderWorker
from .langfuse import Trace


class WorkerManager:
    """Manages render worker processes"""
    
    def __init__(self):
        self.workers: Dict[str, Dict] = {}
        self.max_workers = int(os.getenv("MAX_RENDER_WORKERS", "3"))
        self.running = False
        
    async def start_worker(self, worker_id: Optional[str] = None) -> str:
        """Start a new render worker"""
        if not worker_id:
            worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            
        if worker_id in self.workers:
            raise ValueError(f"Worker {worker_id} already exists")
            
        if len(self.workers) >= self.max_workers:
            raise ValueError(f"Maximum workers ({self.max_workers}) already running")
            
        # Create worker instance
        worker = RenderWorker(worker_id=worker_id)
        
        # Start worker task
        task = asyncio.create_task(worker.start())
        
        # Track worker
        self.workers[worker_id] = {
            "worker": worker,
            "task": task,
            "started_at": datetime.utcnow(),
            "status": "running",
            "processed_jobs": 0,
            "failed_jobs": 0
        }
        
        return worker_id
        
    async def stop_worker(self, worker_id: str) -> bool:
        """Stop a specific worker"""
        if worker_id not in self.workers:
            return False
            
        worker_info = self.workers[worker_id]
        worker = worker_info["worker"]
        task = worker_info["task"]
        
        # Gracefully stop worker
        await worker.stop()
        
        # Cancel task if still running
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        # Update status
        worker_info["status"] = "stopped"
        worker_info["stopped_at"] = datetime.utcnow()
        
        return True
        
    async def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker"""
        if worker_id not in self.workers:
            return False
            
        # Stop existing worker
        await self.stop_worker(worker_id)
        
        # Remove from tracking
        del self.workers[worker_id]
        
        # Start new worker with same ID
        await self.start_worker(worker_id)
        
        return True
        
    async def scale_workers(self, target_count: int) -> Dict[str, int]:
        """Scale workers to target count"""
        current_count = len([w for w in self.workers.values() if w["status"] == "running"])
        
        if target_count > self.max_workers:
            target_count = self.max_workers
            
        if target_count < 0:
            target_count = 0
            
        started = 0
        stopped = 0
        
        if target_count > current_count:
            # Start more workers
            for _ in range(target_count - current_count):
                try:
                    await self.start_worker()
                    started += 1
                except Exception:
                    break
                    
        elif target_count < current_count:
            # Stop some workers
            running_workers = [wid for wid, info in self.workers.items() 
                             if info["status"] == "running"]
            to_stop = running_workers[:current_count - target_count]
            
            for worker_id in to_stop:
                if await self.stop_worker(worker_id):
                    stopped += 1
                    
        return {
            "started": started,
            "stopped": stopped,
            "current_count": len([w for w in self.workers.values() if w["status"] == "running"])
        }
        
    def get_worker_stats(self) -> Dict[str, any]:
        """Get statistics about all workers"""
        running = sum(1 for w in self.workers.values() if w["status"] == "running")
        stopped = sum(1 for w in self.workers.values() if w["status"] == "stopped")
        total_processed = sum(w["processed_jobs"] for w in self.workers.values())
        total_failed = sum(w["failed_jobs"] for w in self.workers.values())
        
        return {
            "total_workers": len(self.workers),
            "running_workers": running,
            "stopped_workers": stopped,
            "max_workers": self.max_workers,
            "total_processed_jobs": total_processed,
            "total_failed_jobs": total_failed,
            "workers": {
                wid: {
                    "status": info["status"],
                    "started_at": info["started_at"].isoformat(),
                    "stopped_at": info.get("stopped_at", {}).isoformat() if info.get("stopped_at") else None,
                    "processed_jobs": info["processed_jobs"],
                    "failed_jobs": info["failed_jobs"]
                }
                for wid, info in self.workers.items()
            }
        }
        
    async def health_check(self) -> Dict[str, any]:
        """Check health of all workers"""
        healthy_workers = 0
        unhealthy_workers = 0
        
        for worker_id, info in self.workers.items():
            if info["status"] == "running" and not info["task"].done():
                healthy_workers += 1
            else:
                unhealthy_workers += 1
                
        return {
            "healthy_workers": healthy_workers,
            "unhealthy_workers": unhealthy_workers,
            "overall_health": "healthy" if unhealthy_workers == 0 else "degraded"
        }
        
    async def start_manager(self):
        """Start the worker manager with initial workers"""
        if self.running:
            return
            
        self.running = True
        
        # Start initial workers (at least 1)
        initial_workers = max(1, min(2, self.max_workers))
        for _ in range(initial_workers):
            try:
                await self.start_worker()
            except Exception as e:
                print(f"Failed to start initial worker: {e}")
                
    async def stop_manager(self):
        """Stop all workers and the manager"""
        if not self.running:
            return
            
        self.running = False
        
        # Stop all running workers
        for worker_id in list(self.workers.keys()):
            await self.stop_worker(worker_id)
            
        self.workers.clear()
        
    async def auto_scale(self, queue_depth: int) -> Dict[str, int]:
        """
        Auto-scale workers based on queue depth
        
        Scaling logic:
        - 0-5 jobs: 1 worker
        - 6-15 jobs: 2 workers  
        - 16+ jobs: 3 workers (max)
        """
        if queue_depth <= 5:
            target = 1
        elif queue_depth <= 15:
            target = 2
        else:
            target = min(3, self.max_workers)
            
        return await self.scale_workers(target)


# Global worker manager instance
worker_manager = WorkerManager()


async def setup_signal_handlers():
    """Setup graceful shutdown signal handlers"""
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down workers...")
        asyncio.create_task(worker_manager.stop_manager())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)