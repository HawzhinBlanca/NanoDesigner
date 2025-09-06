from __future__ import annotations

from typing import Tuple

from ..core.config import settings

# Lazy import backends

def _backend():
    if settings.storage_backend in ("local", "auto"):
        # Prefer local when R2 creds are missing
        from . import storage_local as backend
        return backend
    if settings.storage_backend == "s3" or settings.r2_access_key_id:
        from . import storage_r2 as backend
        return backend
    # Fallback to local
    from . import storage_local as backend
    return backend


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    return _backend().put_object(key, data, content_type)


def get_object(key: str):
    return _backend().get_object(key)


def signed_public_url(key: str, expires_seconds: int = 900) -> str:
    return _backend().signed_public_url(key, expires_seconds)
