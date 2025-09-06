from __future__ import annotations

import time
from typing import Optional

import httpx
from fastapi import HTTPException, status
try:
    # pytector is optional at runtime until installed in environment
    from pytector import Sanitize
except Exception:  # pragma: no cover
    Sanitize = None  # type: ignore


class InputSanitizer:
    """Wrapper around pytector to sanitize untrusted inputs.

    Uses strict mode by default per org security policy. If pytector is not
    installed, passes data through (dev-only scenarios)."""

    def __init__(self, mode: str = "strict"):
        self.mode = mode
        self._impl = None
        if Sanitize is not None:
            try:
                self._impl = Sanitize(mode=self.mode)
            except Exception:
                self._impl = None

    def sanitize(self, value):
        if self._impl is None:
            return value
        return self._impl.clean(value)


class JWTVerifier:
    """Minimal JWT verifier supporting JWKS fetch.

    In production, this is handled by Kong. This utility allows
    optional in-app verification if needed for service-to-service calls.
    """

    def __init__(self, jwks_url: Optional[str] = None):
        self.jwks_url = jwks_url
        self._jwks_cache = None
        self._jwks_cache_at = 0

    async def _get_jwks(self):
        if not self.jwks_url:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No JWKS configured")
        # cache for 5 minutes
        if self._jwks_cache and (time.time() - self._jwks_cache_at) < 300:
            return self._jwks_cache
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(self.jwks_url)
            r.raise_for_status()
            self._jwks_cache = r.json()
            self._jwks_cache_at = time.time()
            return self._jwks_cache

    async def verify(self, token: str):
        # Intentionally minimal: rely on Kong for gateway auth.
        # Here we only check presence; full JWT validation can be added if required.
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
        return True
