from __future__ import annotations

import hashlib
from typing import Callable, Optional

import redis

from ..core.config import settings


_client: Optional[redis.Redis] = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=False)
    return _client


def cache_get_set(key: str, factory: Callable[[], bytes], ttl: int = 86400) -> bytes:
    r = get_client()
    val = r.get(key)
    if val is not None:
        return val  # type: ignore[return-value]
    data = factory()
    r.setex(key, ttl, data)
    return data


def sha1key(*parts) -> str:
    """Generate a SHA1 hash key from multiple parts.
    
    Args:
        *parts: Variable number of parts to hash. None values are converted to empty strings.
        
    Returns:
        str: 40-character hexadecimal SHA1 hash
    """
    h = hashlib.sha1()
    for p in parts:
        # Convert None to empty string, everything else to string
        part_str = "" if p is None else str(p)
        h.update(part_str.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()
