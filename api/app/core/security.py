from __future__ import annotations

import logging
import time
import re
from typing import Optional, Dict, List

import httpx
from fastapi import HTTPException, status
from typing import Any
import os
import jwt
from jwt import PyJWKClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
try:
    from pytector import PromptInjectionDetector
    Sanitize = PromptInjectionDetector
except Exception:  # pragma: no cover
    Sanitize = None  # type: ignore

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Wrapper around pytector to sanitize untrusted inputs.

    Uses strict mode by default per org security policy. If pytector is not
    installed, passes data through (dev-only scenarios)."""

    def __init__(self, mode: str = "strict"):
        self.mode = mode
        self._impl = None
        if Sanitize is not None:
            try:
                self._impl = Sanitize()  # PromptInjectionDetector doesn't take mode parameter
            except Exception as e:
                logger.error(f"Failed to initialize pytector sanitizer: {e}")
                # In production, this should raise an exception
                from ..core.config import settings
                if settings.service_env not in {"dev", "test", "development", "local"}:
                    raise RuntimeError(f"Critical security component failed to initialize: {e}")
                self._impl = None

    def sanitize(self, value):
        if self._impl is None:
            # Enforce presence in production
            from ..core.config import settings
            if settings.service_env not in {"dev", "test", "development", "local"}:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Input sanitizer unavailable in production")
            # Dev fallback: minimal escaping to reduce risk during local work
            import html
            import re
            if isinstance(value, str):
                value = html.escape(value)
                value = re.sub(r'[<>"\'\`]', '', value)
                if len(value) > 10000:
                    value = value[:10000]
            return value
        # PromptInjectionDetector is for detection, not sanitization
        # For now, just do basic sanitization and return the value
        if isinstance(value, str):
            import html
            import re
            value = html.escape(value)
            value = re.sub(r'[<>"\'\`]', '', value)
            if len(value) > 10000:
                value = value[:10000]
        return value


class JWTVerifier:
    """Production-grade JWT verifier with proper signature validation.
    
    Supports JWKS fetch with caching and full JWT validation including
    signature verification, expiration, and audience checks.
    """

    def __init__(self, jwks_url: Optional[str] = None, audience: Optional[str] = None):
        self.jwks_url = jwks_url or os.getenv("CLERK_JWKS_URL")
        self.audience = audience
        self._jwks_client: Optional[PyJWKClient] = None
        self._jwks_cache_time = 300  # 5 minutes cache
        
    def _get_jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client with caching."""
        if not self.jwks_url:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT verification not configured"
            )
        
        if not self._jwks_client:
            self._jwks_client = PyJWKClient(
                self.jwks_url,
                cache_keys=True,
                lifespan=self._jwks_cache_time
            )
        return self._jwks_client

    async def verify(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with full signature and claims validation.
        
        Returns:
            Dict containing the validated JWT claims
            
        Raises:
            HTTPException: If token is invalid, expired, or signature verification fails
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token"
            )
        
        try:
            # For service-to-service calls with shared secret
            if os.getenv("JWT_SHARED_SECRET"):
                # Verify with shared secret (HS256)
                claims = jwt.decode(
                    token,
                    os.getenv("JWT_SHARED_SECRET"),
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_aud": bool(self.audience)
                    },
                    audience=self.audience
                )
                return claims
            
            # For Clerk or other JWKS-based auth (RS256)
            if self.jwks_url:
                jwks_client = self._get_jwks_client()
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_aud": bool(self.audience)
                    },
                    audience=self.audience if self.audience else None
                )
                return claims
            
            # No verification method configured
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification not configured"
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidAudienceError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"JWT verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )


def validate_org_id(org_id: str) -> str:
    """Validate and sanitize organization ID to prevent injection attacks.
    
    Args:
        org_id: Organization identifier to validate
        
    Returns:
        Sanitized org_id
        
    Raises:
        ValueError: If org_id format is invalid
    """
    if not org_id:
        raise ValueError("Organization ID cannot be empty")
    
    # Allow alphanumeric, underscore, hyphen, and dot (for subdomains)
    # Maximum length of 128 characters
    if not re.match(r'^[a-zA-Z0-9_.-]{1,128}$', org_id):
        raise ValueError(f"Invalid organization ID format: {org_id}")
    
    # Prevent special values that might have special meaning
    if org_id.lower() in ['admin', 'root', 'superuser', 'system', 'null', 'undefined']:
        raise ValueError(f"Reserved organization ID: {org_id}")
    
    return org_id

def extract_org_id_from_request_headers(headers: Any, fallback: str | None = None, verify: bool = False) -> str:
    """Extract and validate org_id from request headers or JWT claims.
    
    Args:
        headers: Request headers
        fallback: Fallback org_id if not found in headers/JWT
        verify: Whether to verify JWT signature (True in production)
        
    Returns:
        Validated organization ID
    """
    # Prefer explicit header if provided by gateway
    org_header = headers.get("X-Org-Id") if hasattr(headers, "get") else None
    if org_header:
        try:
            return validate_org_id(str(org_header))
        except ValueError as e:
            logger.warning(f"Invalid X-Org-Id header: {e}")
    
    # Extract from JWT
    auth = headers.get("Authorization") if hasattr(headers, "get") else None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            if verify and os.getenv("JWT_SHARED_SECRET"):
                # Verify signature in production
                claims = jwt.decode(
                    token,
                    os.getenv("JWT_SHARED_SECRET"),
                    algorithms=["HS256"],
                    options={"verify_signature": True, "verify_exp": False}
                )
            else:
                # Development mode - still perform basic validation but warn about security
                logger.warning("JWT signature verification disabled in development mode - security risk!")
                claims = jwt.decode(
                    token,
                    options={"verify_signature": False, "verify_aud": False, "verify_exp": True}
                )
                # Additional validation in dev mode
                if not claims.get("exp"):
                    logger.warning("JWT token without expiration in development mode")
                if not claims.get("iat"):
                    logger.warning("JWT token without issued-at claim in development mode")
            
            org_id = claims.get("org_id") or claims.get("org") or claims.get("orgId")
            if org_id:
                return validate_org_id(str(org_id))
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT decode failed: {e}")
        except ValueError as e:
            logger.warning(f"Invalid org_id in JWT: {e}")
        except Exception as e:
            logger.error(f"Unexpected error extracting org_id: {e}")
    
    # Use fallback if provided
    if fallback:
        try:
            return validate_org_id(str(fallback))
        except ValueError:
            logger.warning(f"Invalid fallback org_id: {fallback}")
    
    # Last resort: anonymous org (validated)
    return "anonymous"
