from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional

import httpx

from ..core.config import settings


class Trace:
    def __init__(self, name: str):
        self.name = name
        self.id = str(uuid.uuid4())
        self.spans: list[dict] = []
        self.logs: list[dict] = []

    def log(self, message: str, level: str = "INFO"):
        """Add a log entry to the trace"""
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message
        })

    @contextmanager
    def span(self, name: str, meta: Optional[Dict[str, Any]] = None):
        start = time.time()
        span = {"name": name, "start": start, "meta": meta or {}}
        try:
            yield span
            span["status"] = "OK"
        except Exception as e:  # noqa: BLE001
            span["status"] = "ERROR"
            span["error"] = str(e)
            raise
        finally:
            span["end"] = time.time()
            span["duration_ms"] = int((span["end"] - start) * 1000)
            self.spans.append(span)

    async def flush(self):
        if not (settings.langfuse_public_key and settings.langfuse_secret_key):
            return
        payload = {
            "traceId": self.id,
            "name": self.name,
            "spans": self.spans,
            "logs": self.logs,
            "service": settings.service_name,
            "env": settings.service_env,
            "region": settings.service_region,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.langfuse_host}/api/public/ingestion",
                headers={
                    "X-Langfuse-Public-Key": settings.langfuse_public_key,
                    "X-Langfuse-Secret-Key": settings.langfuse_secret_key,
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload),
            )
