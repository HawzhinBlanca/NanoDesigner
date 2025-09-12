"""
Application lifecycle management - startup and graceful shutdown
"""
import signal
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
import time
import os
from fastapi import FastAPI

logger = logging.getLogger(__name__)

class LifecycleManager:
    """Manages application lifecycle events"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.is_shutting_down = False
        self.active_requests = 0
        self.start_time = time.time()
        self.connections = []
        
    async def startup(self):
        """Initialize application resources"""
        logger.info("🚀 Starting application...")
        
        # Initialize database connections
        await self.init_database()
        
        # Initialize cache connections
        await self.init_cache()
        
        # Initialize vector database
        await self.init_vector_db()
        
        # Warm up models
        await self.warm_up_models()
        
        # Register signal handlers
        self.register_signal_handlers()
        
        logger.info("✅ Application started successfully")
    
    async def shutdown(self):
        """Graceful shutdown sequence"""
        if self.is_shutting_down:
            return
            
        self.is_shutting_down = True
        logger.info("🛑 Starting graceful shutdown...")
        
        # Stop accepting new requests
        self.shutdown_event.set()
        
        # Wait for active requests to complete (with timeout)
        timeout = 30  # seconds
        start = time.time()
        
        while self.active_requests > 0 and (time.time() - start) < timeout:
            logger.info(f"Waiting for {self.active_requests} active requests to complete...")
            await asyncio.sleep(1)
        
        if self.active_requests > 0:
            logger.warning(f"Forcing shutdown with {self.active_requests} active requests")
        
        # Close all connections
        await self.close_connections()
        
        logger.info("✅ Graceful shutdown complete")
    
    async def init_database(self):
        """Initialize database connection pool"""
        try:
            import asyncpg
            
            # Create connection pool
            pool = await asyncpg.create_pool(
                os.getenv("DATABASE_URL", ""),
                min_size=5,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=60
            )
            
            self.connections.append(("database", pool))
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    async def init_cache(self):
        """Initialize Redis connection pool"""
        try:
            import redis.asyncio as redis
            
            pool = redis.ConnectionPool.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"),
                max_connections=50,
                decode_responses=True
            )
            
            # Test connection
            client = redis.Redis(connection_pool=pool)
            await client.ping()
            
            self.connections.append(("redis", pool))
            logger.info("Redis connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
    
    async def init_vector_db(self):
        """Initialize Qdrant client"""
        try:
            from qdrant_client import AsyncQdrantClient
            
            client = AsyncQdrantClient(
                url=os.getenv("QDRANT_URL", "http://localhost:6333"),
                api_key=os.getenv("QDRANT_API_KEY"),
                timeout=30
            )
            
            # Test connection
            await client.get_collections()
            
            self.connections.append(("qdrant", client))
            logger.info("Qdrant client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
    
    async def warm_up_models(self):
        """Pre-load and warm up ML models"""
        try:
            # This would typically load your models into memory
            # For now, we'll just log
            logger.info("Warming up models...")
            
            # Simulate model loading
            await asyncio.sleep(0.5)
            
            logger.info("Models warmed up successfully")
            
        except Exception as e:
            logger.error(f"Failed to warm up models: {e}")
    
    async def close_connections(self):
        """Close all open connections"""
        for name, connection in self.connections:
            try:
                logger.info(f"Closing {name} connection...")
                
                if hasattr(connection, 'close'):
                    await connection.close()
                elif hasattr(connection, 'terminate'):
                    await connection.terminate()
                    
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")
    
    def register_signal_handlers(self):
        """Register Unix signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.shutdown())
        
        # Register handlers for common termination signals
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, signal_handler)
    
    def track_request_start(self):
        """Track start of a request"""
        self.active_requests += 1
    
    def track_request_end(self):
        """Track end of a request"""
        self.active_requests = max(0, self.active_requests - 1)
    
    @property
    def uptime(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.start_time
    
    @property
    def is_healthy(self) -> bool:
        """Check if application is healthy"""
        return not self.is_shutting_down and self.shutdown_event.is_set() == False

# Global lifecycle manager instance
lifecycle_manager = LifecycleManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    # Startup
    await lifecycle_manager.startup()
    
    yield
    
    # Shutdown
    await lifecycle_manager.shutdown()

# Middleware for request tracking
async def track_requests_middleware(request, call_next):
    """Middleware to track active requests"""
    
    # Don't track health checks
    if request.url.path.startswith("/health"):
        return await call_next(request)
    
    # Check if shutting down
    if lifecycle_manager.is_shutting_down:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"error": "Service is shutting down"}
        )
    
    # Track request
    lifecycle_manager.track_request_start()
    
    try:
        response = await call_next(request)
        return response
    finally:
        lifecycle_manager.track_request_end()