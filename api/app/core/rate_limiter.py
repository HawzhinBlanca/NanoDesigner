"""Production-grade Redis-based rate limiter with sliding window algorithm."""

import time
import logging
from typing import Optional, Tuple
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..services.redis import get_client
from ..core.config import settings

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Redis-based rate limiter using sliding window algorithm.
    
    This implementation provides:
    - Distributed rate limiting across multiple servers
    - Sliding window for smooth rate limiting
    - Automatic key expiration to prevent memory leaks
    - Configurable per-endpoint rate limits
    """
    
    def __init__(
        self,
        requests_per_minute: int = 100,
        burst_size: int = 20,
        key_prefix: str = "rate_limit"
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.key_prefix = key_prefix
        self.window_seconds = 60  # 1 minute window
        
    def _get_key(self, identifier: str, endpoint: str = "") -> str:
        """Generate Redis key for rate limiting."""
        if endpoint:
            return f"{self.key_prefix}:{endpoint}:{identifier}"
        return f"{self.key_prefix}:{identifier}"
    
    def check_rate_limit(self, identifier: str, endpoint: str = "") -> Tuple[bool, int, int]:
        """Check if request is within rate limit.
        
        Returns:
            Tuple of (allowed, remaining_requests, reset_timestamp)
        """
        try:
            redis_client = get_client()
            key = self._get_key(identifier, endpoint)
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window BEFORE adding new one
            pipe.zcard(key)
            
            # Execute first to get current count
            results = pipe.execute()
            request_count = results[1]  # Current count in window
            
            # Check if within limits BEFORE adding the request
            if request_count >= self.requests_per_minute:
                # Get oldest request timestamp for reset time
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1]) + self.window_seconds
                else:
                    reset_time = int(current_time) + self.window_seconds
                    
                return False, 0, reset_time
            
            # Only add the request if it's allowed
            # Use microsecond precision to ensure unique entries
            request_id = f"{current_time:.6f}:{id(current_time)}"
            redis_client.zadd(key, {request_id: current_time})
            redis_client.expire(key, self.window_seconds + 10)
            
            remaining = self.requests_per_minute - request_count - 1
            reset_time = int(current_time) + self.window_seconds
            
            return True, max(0, remaining), reset_time
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # On Redis failure, allow request but log the issue
            # In production, you might want to fail closed instead
            return True, -1, 0
    
    def reset_limit(self, identifier: str, endpoint: str = "") -> bool:
        """Reset rate limit for an identifier (useful for testing)."""
        try:
            redis_client = get_client()
            key = self._get_key(identifier, endpoint)
            redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based rate limiting middleware with proper DoS protection."""
    
    def __init__(
        self, 
        app: ASGIApp,
        requests_per_minute: int = 100,
        burst_size: int = 20,
        use_redis: bool = True  # Allow fallback to memory for dev
    ):
        super().__init__(app)
        self.use_redis = use_redis and settings.redis_url
        
        if self.use_redis:
            self.limiter = RedisRateLimiter(
                requests_per_minute=requests_per_minute,
                burst_size=burst_size
            )
            logger.info("Using Redis-based rate limiter")
        else:
            # Fallback to simple memory-based limiter for development
            # This should NOT be used in production
            logger.warning("⚠️  Using memory-based rate limiter - NOT FOR PRODUCTION")
            self.requests_per_minute = requests_per_minute
            self.burst_size = burst_size
            self.clients = {}
            self._last_cleanup = time.time()
            self._max_clients = 1000  # Hard limit to prevent memory exhaustion
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting based on client IP or API key."""
        
        # Extract identifier (IP or API key)
        identifier = self._get_identifier(request)
        endpoint = request.url.path
        
        if self.use_redis:
            # Redis-based rate limiting
            allowed, remaining, reset_time = self.limiter.check_rate_limit(
                identifier, endpoint
            )
            
            if not allowed:
                retry_after = max(1, reset_time - int(time.time()))
                return JSONResponse(
                    content={
                        "error": "RateLimitExceeded",
                        "message": f"Rate limit of {self.limiter.requests_per_minute} requests per minute exceeded",
                        "retry_after_seconds": retry_after
                    },
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(self.limiter.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(retry_after)
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
            return response
            
        else:
            # Fallback memory-based limiter (dev only)
            return await self._memory_rate_limit(request, call_next, identifier)
    
    def _get_identifier(self, request: Request) -> str:
        """Extract identifier for rate limiting."""
        
        # Check for API key first
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"api:{api_key[:16]}"  # Use prefix of API key
        
        # Check for authenticated user
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        return f"ip:{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        
        # Check common proxy headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in case of multiple proxies
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"
    
    async def _memory_rate_limit(self, request: Request, call_next, identifier: str):
        """Memory-based rate limiting (development only)."""
        
        current_time = time.time()
        
        # Aggressive cleanup to prevent memory exhaustion
        if len(self.clients) > self._max_clients:
            # Remove oldest entries
            sorted_clients = sorted(
                self.clients.items(),
                key=lambda x: x[1].get('last_request', 0)
            )
            # Keep only half of max clients
            keep_count = self._max_clients // 2
            self.clients = dict(sorted_clients[-keep_count:])
            logger.warning(f"Emergency cleanup: reduced clients from {len(sorted_clients)} to {keep_count}")
        
        # Periodic cleanup
        if current_time - self._last_cleanup > 60:  # Every minute
            self._cleanup_old_entries(current_time)
            self._last_cleanup = current_time
        
        # Get or create client data
        if identifier not in self.clients:
            self.clients[identifier] = {
                'requests': [],
                'last_request': current_time
            }
        
        client_data = self.clients[identifier]
        
        # Remove requests older than 1 minute
        minute_ago = current_time - 60
        client_data['requests'] = [
            req_time for req_time in client_data['requests'] 
            if req_time > minute_ago
        ]
        
        # Check rate limit
        if len(client_data['requests']) >= self.requests_per_minute:
            return JSONResponse(
                content={
                    "error": "RateLimitExceeded",
                    "message": f"Rate limit of {self.requests_per_minute} requests per minute exceeded (memory-based)",
                    "mode": "development"
                },
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60"
                }
            )
        
        # Record this request
        client_data['requests'].append(current_time)
        client_data['last_request'] = current_time
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(client_data['requests']))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old entries to prevent memory leaks."""
        cutoff_time = current_time - 300  # Remove entries older than 5 minutes
        old_count = len(self.clients)
        self.clients = {
            ip: data for ip, data in self.clients.items() 
            if data['last_request'] > cutoff_time
        }
        cleaned_count = old_count - len(self.clients)
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} old rate limiting entries")


# Endpoint-specific rate limits configuration
ENDPOINT_RATE_LIMITS = {
    "/render": {"requests_per_minute": 30, "burst_size": 5},  # Expensive operation
    "/async-render": {"requests_per_minute": 20, "burst_size": 3},
    "/ingest": {"requests_per_minute": 50, "burst_size": 10},
    "/upload": {"requests_per_minute": 20, "burst_size": 5},
    "/critique": {"requests_per_minute": 60, "burst_size": 15},
    "/canon/derive": {"requests_per_minute": 40, "burst_size": 8},
    # Default for all other endpoints
    "default": {"requests_per_minute": 100, "burst_size": 20}
}


def get_endpoint_limits(path: str) -> dict:
    """Get rate limits for specific endpoint."""
    # Normalize path (remove query params and trailing slash)
    clean_path = path.split("?")[0].rstrip("/")
    
    # Check for exact match
    if clean_path in ENDPOINT_RATE_LIMITS:
        return ENDPOINT_RATE_LIMITS[clean_path]
    
    # Check for prefix match (for parameterized routes)
    for endpoint, limits in ENDPOINT_RATE_LIMITS.items():
        if endpoint != "default" and clean_path.startswith(endpoint):
            return limits
    
    return ENDPOINT_RATE_LIMITS["default"]