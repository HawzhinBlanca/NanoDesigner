from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Callable, Optional, Dict, Any

import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from ..core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()
_pool_health_check_time = 0
_pool_health_check_interval = 30  # seconds


def get_client() -> redis.Redis:
    """Get Redis client with proper connection pooling, health checks, and error handling.
    
    Implements:
    - Thread-safe pool creation
    - Periodic health checks
    - Automatic pool recreation on failure
    - Connection validation
    """
    global _pool, _pool_health_check_time
    
    # Check if pool needs health check or recreation
    current_time = time.time()
    needs_health_check = (
        _pool is not None and 
        current_time - _pool_health_check_time > _pool_health_check_interval
    )
    
    if needs_health_check:
        if not _validate_pool_health(_pool):
            logger.warning("Redis pool health check failed, recreating pool")
            cleanup()
            _pool = None
    
    # Create pool if needed (thread-safe)
    if _pool is None:
        with _pool_lock:
            # Double-check after acquiring lock
            if _pool is None:
                try:
                    _pool = _create_connection_pool()
                    _pool_health_check_time = current_time
                    logger.info("Redis connection pool initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Redis connection pool: {e}")
                    raise RedisError(f"Cannot establish Redis connection: {e}")
    
    try:
        client = redis.Redis(connection_pool=_pool)
        # Quick validation ping
        client.ping()
        return client
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed: {e}")
        # Mark pool for recreation on next call
        cleanup()
        raise RedisError(f"Redis connection lost: {e}")

def _create_connection_pool() -> ConnectionPool:
    """Create a new Redis connection pool with optimized settings."""
    pool_config = {
        "max_connections": 100,  # Production load capacity
        "retry_on_timeout": True,
        "retry_on_error": [ConnectionError, TimeoutError],
        "health_check_interval": 30,
        "decode_responses": False,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "socket_keepalive": True,
        "socket_keepalive_options": {
            # TCP keepalive options for better connection stability
            1: 1,  # TCP_KEEPIDLE: start keepalive after 1 second
            2: 1,  # TCP_KEEPINTVL: interval between keepalive probes
            3: 3,  # TCP_KEEPCNT: number of keepalive probes
        }
    }
    
    return ConnectionPool.from_url(settings.redis_url, **pool_config)

def _validate_pool_health(pool: Optional[ConnectionPool]) -> bool:
    """Validate that the connection pool is healthy.
    
    Args:
        pool: The connection pool to validate
        
    Returns:
        True if pool is healthy, False otherwise
    """
    if pool is None:
        return False
    
    try:
        # Try to get a connection and ping
        test_client = redis.Redis(connection_pool=pool)
        test_client.ping()
        
        # Check pool statistics
        pool_stats = pool.connection_kwargs
        in_use = pool.connection_pool.in_use_connections if hasattr(pool, 'connection_pool') else 0
        
        # Log pool statistics for monitoring
        logger.debug(f"Redis pool stats - In use: {in_use}, Max: {pool_stats.get('max_connections', 'N/A')}")
        
        return True
    except Exception as e:
        logger.warning(f"Redis pool health check failed: {e}")
        return False


def cache_get_set(key: str, factory: Callable[[], bytes], ttl: int = 86400) -> bytes:
    """Get value from cache or compute and store it.
    
    Includes proper error handling and fallback to factory on cache failure.
    
    Args:
        key: Cache key
        factory: Function to generate value if not in cache
        ttl: Time to live in seconds
        
    Returns:
        Cached or newly computed value
    """
    try:
        r = get_client()
        val = r.get(key)
        if val is not None:
            return val  # type: ignore[return-value]
    except RedisError as e:
        logger.warning(f"Redis get failed for key {key}: {e}")
        # Fall through to compute value
    
    # Compute value
    data = factory()
    
    # Try to cache it (best effort)
    try:
        r = get_client()
        r.setex(key, ttl, data)
    except RedisError as e:
        logger.warning(f"Redis setex failed for key {key}: {e}")
        # Still return the computed value
    
    return data


def sha256key(*parts) -> str:
    """Generate a SHA256 hash key from multiple parts.
    
    Optimized for common use cases (strings and simple types).
    Uses incremental hashing to avoid memory overhead of concatenation.
    
    Args:
        *parts: Variable number of parts to hash. None values are converted to empty strings.
        
    Returns:
        str: 64-character hexadecimal SHA256 hash
    """
    # Use incremental hashing
    hasher = hashlib.sha256()
    
    # Handle edge case where no parts are provided
    if not parts:
        return hasher.hexdigest()
    
    # Pre-allocate separator as bytes to avoid repeated encoding
    SEP = b"|"
    
    # Process each part
    for i, part in enumerate(parts):
        if i > 0:
            hasher.update(SEP)
        
        # Fast path for common types
        if part is None:
            hasher.update(b"")  # Treat None as empty
        elif isinstance(part, str):
            # Most common case - optimize for strings
            hasher.update(part.encode("utf-8"))
        elif isinstance(part, bytes):
            # Already bytes, no conversion needed
            hasher.update(part)
        elif isinstance(part, (int, float)):
            # Numbers - include type prefix to avoid collisions with strings
            type_prefix = "i:" if isinstance(part, int) else "f:"
            hasher.update((type_prefix + repr(part)).encode("ascii"))
        else:
            # Complex types - use str() for simplicity
            # This is rare in cache keys, so optimize for common case
            hasher.update(str(part).encode("utf-8"))
    
    return hasher.hexdigest()

def sha1key(*parts) -> str:
    """Generate a SHA1 hash key from multiple parts (test compatibility).

    Maintains 40-char length expected by legacy tests.
    """
    hasher = hashlib.sha1()
    SEP = b"|"
    if not parts:
        return hasher.hexdigest()
    for i, part in enumerate(parts):
        if i > 0:
            hasher.update(SEP)
        if part is None:
            hasher.update(b"n:")
        elif isinstance(part, bytes):
            hasher.update(b"b:")
            hasher.update(part)
        elif isinstance(part, str):
            # Prefix strings so sha1key() != sha1key("")
            hasher.update(b"s:")
            hasher.update(part.encode("utf-8"))
        elif isinstance(part, (int, float)):
            prefix = b"i:" if isinstance(part, int) else b"f:"
            hasher.update(prefix + str(part).encode("ascii"))
        else:
            hasher.update(b"o:")
            hasher.update(str(part).encode("utf-8"))
    return hasher.hexdigest()


def cleanup():
    """Clean up Redis connection pool safely."""
    global _pool, _pool_health_check_time
    
    with _pool_lock:
        if _pool:
            try:
                # Disconnect all connections
                _pool.disconnect(inuse_connections=True)
                logger.info("Redis connection pool cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up Redis pool: {e}")
            finally:
                _pool = None
                _pool_health_check_time = 0

# Backwards-compatible aliases
get_redis_client = get_client
