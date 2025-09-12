"""
Atomic Redis operations for race-condition-free caching.

This module provides production-grade atomic cache operations that prevent
duplicate API calls, cache stampedes, and race conditions in high-concurrency
environments.
"""

from __future__ import annotations

import json
import time
import logging
import asyncio
import random
from typing import Any, Callable, Optional, TypeVar, Union, Awaitable
from functools import wraps
import hashlib
import uuid

import redis
from redis.exceptions import RedisError, LockError

from ..core.config import settings
from .redis import get_client, sha256key

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AtomicRedisCache:
    """
    Production-grade atomic Redis cache with race condition prevention.
    
    Features:
    - Atomic check-and-set operations
    - Distributed locking for cache misses
    - Stale-while-revalidate pattern
    - Circuit breaker for Redis failures
    - Automatic retry with exponential backoff
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_ttl: int = 3600,
        lock_timeout: int = 30,
        stale_ttl: int = 86400,
        max_retries: int = 3
    ):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.lock_timeout = lock_timeout
        self.stale_ttl = stale_ttl  # How long to keep stale data
        self.max_retries = max_retries
        self._circuit_breaker_open = False
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_reset_time = 60
        self._last_failure_time = 0
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be open."""
        if not self._circuit_breaker_open:
            return False
        
        # Check if enough time has passed to reset
        if time.time() - self._last_failure_time > self._circuit_breaker_reset_time:
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
        # logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def _record_failure(self):
        """Record a Redis failure for circuit breaker."""
        self._circuit_breaker_failures += 1
        self._last_failure_time = time.time()
        
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            self._circuit_breaker_open = True
        # logger.warning(f"Circuit breaker opened after {self._circuit_breaker_failures} failures")
    
    def _record_success(self):
        """Record a successful Redis operation."""
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = max(0, self._circuit_breaker_failures - 1)
    
    def generate_cache_key(self, *parts: Any) -> str:
        """Generate a deterministic cache key from parts."""
        hasher = hashlib.sha256()
        
        for part in parts:
            if part is None:
                hasher.update(b"none")
            elif isinstance(part, (dict, list)):
                hasher.update(json.dumps(part, sort_keys=True).encode())
            else:
                hasher.update(str(part).encode())
            hasher.update(b"|")  # Separator
        
        return f"cache:{hasher.hexdigest()}"
    
    def get_with_lock(
        self,
        key: str,
        factory: Callable[[], T],
        ttl: Optional[int] = None,
        use_stale: bool = True
    ) -> T:
        """
        Get value from cache with distributed locking for factory execution.
        
        This prevents the "thundering herd" problem where multiple processes
        simultaneously try to regenerate the same cached value.
        
        Args:
            key: Cache key
            factory: Function to generate value if not cached
            ttl: Time to live in seconds
            use_stale: Whether to use stale data while regenerating
            
        Returns:
            Cached or newly generated value
        """
        if self._check_circuit_breaker():
        # logger.warning("Circuit breaker open, executing factory directly")
            return factory()
        
        ttl = ttl or self.default_ttl
        lock_key = f"{key}:lock"
        stale_key = f"{key}:stale"
        
        try:
            # Step 1: Try to get fresh value
            value = self.redis.get(key)
            if value is not None:
                self._record_success()
                # Handle both string and bytes
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                return json.loads(value)
            
            # Step 2: Try to acquire lock for regeneration
            lock = self.redis.lock(
                lock_key,
                timeout=self.lock_timeout,
                blocking_timeout=0.1  # Don't block long
            )
            
            if lock.acquire(blocking=False):
                try:
                    # Double-check after acquiring lock (another process might have set it)
                    value = self.redis.get(key)
                    if value is not None:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8')
                        return json.loads(value)
                    
                    # Check for stale value to return while regenerating
                    stale_value = None
                    if use_stale:
                        stale_data = self.redis.get(stale_key)
                        if stale_data:
                            if isinstance(stale_data, bytes):
                                stale_data = stale_data.decode('utf-8')
                            stale_value = json.loads(stale_data)
        # logger.info(f"Using stale value for {key} while regenerating")
                    
                    # Generate new value
        # logger.info(f"Cache miss for {key}, generating new value")
                    new_value = factory()
                    
                    # Store in cache with pipeline for atomicity
                    pipe = self.redis.pipeline()
                    
                    # Set fresh value
                    pipe.setex(key, ttl, json.dumps(new_value))
                    
                    # Set stale backup (longer TTL)
                    if use_stale:
                        pipe.setex(stale_key, self.stale_ttl, json.dumps(new_value))
                    
                    pipe.execute()
                    self._record_success()
                    
                    return new_value
                    
                finally:
                    try:
                        lock.release()
                    except LockError:
                        pass  # Lock expired, someone else owns it now
            
            else:
                # Someone else is regenerating, wait or use stale
        # logger.info(f"Lock held by another process for {key}")
                
                # Wait a bit for the other process with jitter
                for _ in range(10):  # Wait up to 1 second
                    time.sleep(0.05 + random.uniform(0, 0.05))
                    value = self.redis.get(key)
                    if value is not None:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8')
                        return json.loads(value)
                
                # Try stale value
                if use_stale:
                    stale_data = self.redis.get(stale_key)
                    if stale_data:
                        if isinstance(stale_data, bytes):
                            stale_data = stale_data.decode('utf-8')
        # logger.warning(f"Using stale value for {key} (lock timeout)")
                        return json.loads(stale_data)
                
                # Last resort: generate ourselves
        # logger.warning(f"Lock timeout for {key}, generating value anyway")
                return factory()
                
        except RedisError as e:
        # logger.error(f"Redis error for key {key}: {e}")
            self._record_failure()
            
            # Try stale value on Redis error
            if use_stale:
                try:
                    stale_data = self.redis.get(stale_key)
                    if stale_data:
                        if isinstance(stale_data, bytes):
                            stale_data = stale_data.decode('utf-8')
        # logger.warning(f"Using stale value for {key} (Redis error)")
                        return json.loads(stale_data)
                except:
                    pass
            
            # Fall back to factory
            return factory()
    
    async def async_get_with_lock(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: Optional[int] = None,
        use_stale: bool = True
    ) -> T:
        """
        Async version of get_with_lock for async factories.
        """
        if self._check_circuit_breaker():
        # logger.warning("Circuit breaker open, executing factory directly")
            return await factory()
        
        ttl = ttl or self.default_ttl
        lock_key = f"{key}:lock"
        stale_key = f"{key}:stale"
        
        try:
            # Try to get fresh value
            value = self.redis.get(key)
            if value is not None:
                self._record_success()
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                return json.loads(value)
            
            # Try to acquire lock
            lock = self.redis.lock(
                lock_key,
                timeout=self.lock_timeout,
                blocking_timeout=0.1
            )
            
            if lock.acquire(blocking=False):
                try:
                    # Double-check
                    value = self.redis.get(key)
                    if value is not None:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8')
                        return json.loads(value)
                    
                    # Generate new value
                    # Temporarily disable logging to avoid scoping issues
                    # logger.info(f"Async cache miss for {key}, generating new value")
                    new_value = await factory()
                    
                    # Store in cache
                    pipe = self.redis.pipeline()
                    pipe.setex(key, ttl, json.dumps(new_value))
                    if use_stale:
                        pipe.setex(stale_key, self.stale_ttl, json.dumps(new_value))
                    pipe.execute()
                    
                    self._record_success()
                    return new_value
                    
                finally:
                    try:
                        lock.release()
                    except LockError:
                        pass
            
            else:
                # Wait for other process with jitter
                for _ in range(10):
                    await asyncio.sleep(0.05 + random.uniform(0, 0.05))
                    value = self.redis.get(key)
                    if value is not None:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8')
                        return json.loads(value)
                
                # Try stale or generate
                if use_stale:
                    stale_data = self.redis.get(stale_key)
                    if stale_data:
                        if isinstance(stale_data, bytes):
                            stale_data = stale_data.decode('utf-8')
                        return json.loads(stale_data)
                
                return await factory()
                
        except RedisError as e:
        # logger.error(f"Redis error for key {key}: {e}")
            self._record_failure()
            return await factory()
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry and its stale backup.
        """
        try:
            stale_key = f"{key}:stale"
            pipe = self.redis.pipeline()
            pipe.delete(key)
            pipe.delete(stale_key)
            results = pipe.execute()
            self._record_success()
            return any(results)
        except RedisError as e:
        # logger.error(f"Failed to invalidate {key}: {e}")
            self._record_failure()
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        WARNING: Use carefully in production as KEYS command can be slow.
        """
        try:
            count = 0
            # Use SCAN instead of KEYS for production
            for key in self.redis.scan_iter(match=pattern, count=100):
                if self.redis.delete(key):
                    count += 1
                # Also delete stale versions
                stale_key = f"{key.decode() if isinstance(key, bytes) else key}:stale"
                if self.redis.delete(stale_key):
                    count += 1
            
            self._record_success()
        # logger.info(f"Invalidated {count} keys matching pattern {pattern}")
            return count
        except RedisError as e:
        # logger.error(f"Failed to invalidate pattern {pattern}: {e}")
            self._record_failure()
            return 0


def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    use_stale: bool = True
):
    """
    Decorator for caching function results with atomic operations.
    
    Example:
        @cached(ttl=300, key_prefix="user_data")
        def get_user_data(user_id: str) -> dict:
            # Expensive operation
            return fetch_from_database(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from ..services.redis import get_client
            
            redis_client = get_client()
            cache = AtomicRedisCache(redis_client)
            
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = cache.generate_cache_key(*key_parts)
            
            # Use atomic get with lock
            return cache.get_with_lock(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl=ttl,
                use_stale=use_stale
            )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from ..services.redis import get_client
            
            redis_client = get_client()
            cache = AtomicRedisCache(redis_client)
            
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = cache.generate_cache_key(*key_parts)
            
            # Use atomic async get with lock
            return await cache.async_get_with_lock(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl=ttl,
                use_stale=use_stale
            )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


# Simple AtomicCache class for backward compatibility
class AtomicCache:
    """Simple atomic cache wrapper for backward compatibility."""
    def __init__(self) -> None:
        try:
            self.r = get_client()
            self._cache = AtomicRedisCache(self.r)
            self._redis_available = True
        except Exception:
            self.r = None
            self._cache = None
            self._redis_available = False
            self._memory_cache = {}

    def generate_cache_key(self, *parts: Any) -> str:
        return sha256key(*parts)

    async def async_get_with_lock(self, key: str, factory: Callable[[], Any], ttl: int = 86400, use_stale: bool = True) -> Any:
        if self._redis_available and self._cache:
            try:
                return await self._cache.async_get_with_lock(key, factory, ttl, use_stale)
            except Exception:
                # Redis failed, fall back to memory cache
                pass
        
        # Use in-memory cache as fallback
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        result = await factory()
        self._memory_cache[key] = result
        return result

# Global cache instances
_global_cache: Optional[AtomicRedisCache] = None
_simple_cache: Optional[AtomicCache] = None

def get_atomic_cache() -> Optional[AtomicCache]:
    """Get global atomic cache instance (backward compatible)."""
    global _simple_cache
    if _simple_cache is None:
        try:
            _simple_cache = AtomicCache()
        except Exception:
            # Return None if cache can't be initialized
            return None
    return _simple_cache