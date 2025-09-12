from __future__ import annotations

from typing import Tuple
from ..core.security import extract_org_id_from_request_headers

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


def put_quarantine(project_id: str, filename: str, data: bytes, content_type: str | None = None, org_id: str | None = None) -> str:
    """Store file under quarantine/ prefix and return key."""
    import uuid
    safe_filename = filename or "upload.bin"
    prefix = f"org/{org_id}/" if org_id else ""
    key = f"{prefix}quarantine/{project_id}/{uuid.uuid4()}_{safe_filename}"
    _backend().put_object(key, data, content_type or "application/octet-stream")
    return key


def promote_quarantine_to_public(key: str) -> str:
    """Promote a quarantine key to public/ and return new key.

    Supports keys with optional org/ prefix, e.g.:
    - "quarantine/<project>/<file>"
    - "org/<org_id>/quarantine/<project>/<file>"
    """
    # Locate the quarantine segment anywhere in the key
    idx = key.find("quarantine/")
    if idx == -1:
        return key
    public_key = key[:idx] + key[idx:].replace("quarantine/", "public/", 1)
    data = _backend().get_object(key)
    if data is None:
        raise FileNotFoundError(key)
    _backend().put_object(public_key, data, "application/octet-stream")
    return public_key
