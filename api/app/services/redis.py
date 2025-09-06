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


def sha1key(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()
