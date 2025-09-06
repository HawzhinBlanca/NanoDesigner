from __future__ import annotations

import os
import pathlib
import mimetypes
from typing import Optional

from ..core.config import settings


def _ensure_dir(path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    base = pathlib.Path(settings.local_storage_dir)
    dest = base / key
    _ensure_dir(str(dest))
    with open(dest, "wb") as f:
        f.write(data)


def get_object(key: str) -> bytes | None:
    base = pathlib.Path(settings.local_storage_dir)
    src = base / key
    if not src.exists():
        return None
    return src.read_bytes()


def signed_public_url(key: str, expires_seconds: int = 900) -> str:
    # Local dev: serve via /static/ route
    return f"{settings.service_base_url}/static/{key}"


