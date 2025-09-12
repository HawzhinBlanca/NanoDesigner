"""
Security Headers Middleware for NanoDesigner API
Implements comprehensive security headers to protect against common attacks
"""

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import hashlib
import secrets
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds comprehensive security headers to all API responses
    """
    
    def __init__(self, app, strict: bool = True):
        super().__init__(app)
        self.strict = strict
        self.environment = os.getenv("ENVIRONMENT", "production")
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate nonce for CSP
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers based on environment
        if self.environment == "production" or self.strict:
            # Strict Transport Security (HSTS)
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
            
            # Content Security Policy (CSP)
            csp_directives = [
                "default-src 'self'",
                # No unsafe-inline/eval in production; use nonce for any inline script that might be added
                f"script-src 'self' 'nonce-{nonce}' https://*.clerk.accounts.dev https://*.clerk.com https://*.sentry.io",
                # Avoid unsafe-inline for styles in API responses; allow Google Fonts stylesheet
                "style-src 'self' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https: blob:",
                # Limit connect-src to self + OpenRouter API; extend via gateway if needed
                "connect-src 'self' https://api.openrouter.ai",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "upgrade-insecure-requests"
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        else:
            # Relaxed CSP for development
            csp_directives = [
                "default-src *",
                "script-src * 'unsafe-inline' 'unsafe-eval'",
                "style-src * 'unsafe-inline'",
                "img-src * data: blob:",
                "connect-src *",
                "frame-ancestors *"
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # X-Frame-Options - Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options - Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection - Enable XSS filter (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy - Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        permissions = [
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        # X-Permitted-Cross-Domain-Policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # X-Download-Options - Prevent IE from executing downloads
        response.headers["X-Download-Options"] = "noopen"
        
        # Cache-Control for sensitive data
        if request.url.path.startswith("/api/auth") or request.url.path.startswith("/api/user"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Remove sensitive headers
        headers_to_remove = ["Server", "X-Powered-By", "X-AspNet-Version"]
        for header in headers_to_remove:
            response.headers.pop(header, None)
        
        # Add custom security headers
        response.headers["X-Request-ID"] = request.state.request_id if hasattr(request.state, "request_id") else secrets.token_hex(16)
        
        return response


class ContentTypeValidationMiddleware(BaseHTTPMiddleware):
    """
    Validates Content-Type headers for POST/PUT/PATCH requests
    """
    
    ALLOWED_CONTENT_TYPES = {
        "application/json",
        "multipart/form-data",
        "application/x-www-form-urlencoded"
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only validate for methods that should have content
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            
            # Check if content-type is allowed
            if content_type and not any(
                content_type.startswith(allowed) 
                for allowed in self.ALLOWED_CONTENT_TYPES
            ):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported Media Type",
                        "message": f"Content-Type '{content_type}' is not supported",
                        "allowed": list(self.ALLOWED_CONTENT_TYPES)
                    }
                )
        
        return await call_next(request)


def get_security_headers(strict: bool = True) -> dict:
    """
    Returns a dictionary of security headers
    Can be used for manual header setting
    """
    headers = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Permitted-Cross-Domain-Policies": "none",
        "X-Download-Options": "noopen"
    }
    
    if strict:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
    return headers
