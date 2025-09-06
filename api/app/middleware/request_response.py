"""Request/Response middleware for consistent API behavior.

This middleware ensures consistent request handling, response formatting,
timing, logging, and error handling across all API endpoints.
"""

from __future__ import annotations

import json
import time
import logging
import traceback
from typing import Callable, Optional
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.responses import (
    ResponseMeta,
    create_error_response,
    create_validation_error_response
)
from ..models.exceptions import (
    SGDBaseException,
    OpenRouterException,
    GuardrailsValidationException,
    ContentPolicyViolationException,
    ValidationError
)

logger = logging.getLogger(__name__)

class RequestResponseMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent request/response handling."""
    
    def __init__(
        self,
        app: ASGIApp,
        add_request_id: bool = True,
        log_requests: bool = True,
        log_responses: bool = True,
        include_processing_time: bool = True,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        max_response_size: int = 100 * 1024 * 1024  # 100MB
    ):
        super().__init__(app)
        self.add_request_id = add_request_id
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.include_processing_time = include_processing_time
        self.max_request_size = max_request_size
        self.max_response_size = max_response_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with consistent handling."""
        
        # Generate request ID
        request_id = str(uuid4())
        
        # Add request ID to request state
        if self.add_request_id:
            request.state.request_id = request_id
            
        # Record start time
        start_time = time.time()
        
        # Log incoming request
        if self.log_requests:
            await self._log_request(request, request_id)
        
        # Validate request size
        if hasattr(request, 'headers') and 'content-length' in request.headers:
            content_length = int(request.headers.get('content-length', 0))
            if content_length > self.max_request_size:
                return await self._create_error_response(
                    "Request too large",
                    "REQUEST_TOO_LARGE",
                    f"Request size {content_length} exceeds maximum {self.max_request_size} bytes",
                    request_id=request_id,
                    status_code=413
                )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Enhance response with metadata
            enhanced_response = await self._enhance_response(
                response, 
                request_id, 
                processing_time_ms
            )
            
            # Log response
            if self.log_responses:
                await self._log_response(
                    request, 
                    enhanced_response, 
                    request_id, 
                    processing_time_ms
                )
            
            return enhanced_response
            
        except Exception as e:
            # Handle unexpected errors
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Unhandled exception in request processing",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "traceback": traceback.format_exc()
                },
                exc_info=True
            )
            
            return await self._create_error_response(
                "Internal server error",
                "INTERNAL_ERROR", 
                "An unexpected error occurred while processing your request",
                request_id=request_id,
                processing_time_ms=processing_time_ms,
                status_code=500
            )

    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request details."""
        
        # Basic request info
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "user_agent": request.headers.get("user-agent", ""),
            "remote_addr": self._get_client_ip(request)
        }
        
        # Add auth info if present
        if "authorization" in request.headers:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                log_data["auth_type"] = "bearer"
                # Don't log the actual token, just indicate presence
                log_data["auth_present"] = True
            else:
                log_data["auth_type"] = "other"
        
        # Add content type and length
        log_data["content_type"] = request.headers.get("content-type", "")
        log_data["content_length"] = request.headers.get("content-length", 0)
        
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra=log_data
        )

    async def _log_response(
        self, 
        request: Request, 
        response: Response, 
        request_id: str, 
        processing_time_ms: int
    ):
        """Log outgoing response details."""
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "processing_time_ms": processing_time_ms,
            "response_size": len(getattr(response, 'body', b''))
        }
        
        # Add response headers
        if hasattr(response, 'headers'):
            log_data["content_type"] = response.headers.get("content-type", "")
            log_data["cache_control"] = response.headers.get("cache-control", "")
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
            log_message = f"Server error response: {response.status_code}"
        elif response.status_code >= 400:
            log_level = logging.WARNING  
            log_message = f"Client error response: {response.status_code}"
        else:
            log_level = logging.INFO
            log_message = f"Successful response: {response.status_code}"
        
        logger.log(
            log_level,
            f"{log_message} for {request.method} {request.url.path} ({processing_time_ms}ms)",
            extra=log_data
        )

    async def _enhance_response(
        self, 
        response: Response, 
        request_id: str, 
        processing_time_ms: int
    ) -> Response:
        """Enhance response with consistent metadata."""
        
        # Add standard headers
        if self.add_request_id:
            response.headers["X-Request-ID"] = request_id
            
        if self.include_processing_time:
            response.headers["X-Processing-Time"] = f"{processing_time_ms}ms"
            
        response.headers["X-API-Version"] = "1.0.0"
        
        # For JSON responses, enhance the body with metadata
        if (hasattr(response, 'media_type') and 
            response.media_type == 'application/json' and
            hasattr(response, 'body')):
            
            try:
                # Parse existing response body
                body = json.loads(response.body)
                
                # Add meta information if not present
                if isinstance(body, dict) and 'meta' not in body:
                    body['meta'] = {
                        "request_id": request_id,
                        "timestamp": time.time(),
                        "version": "1.0.0",
                        "processing_time_ms": processing_time_ms
                    }
                    
                    # Create new response with enhanced body
                    return JSONResponse(
                        content=body,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
                    
            except (json.JSONDecodeError, AttributeError):
                # If we can't parse/enhance the body, return original response
                pass
        
        return response

    async def _create_error_response(
        self,
        message: str,
        error_code: str,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        status_code: int = 500
    ) -> JSONResponse:
        """Create a standardized error response."""
        
        error_response = create_error_response(
            message=message,
            error_code=error_code,
            error_message=error_message,
            request_id=request_id,
            processing_time_ms=processing_time_ms
        )
        
        headers = {
            "X-API-Version": "1.0.0"
        }
        
        if request_id:
            headers["X-Request-ID"] = request_id
            
        if processing_time_ms is not None:
            headers["X-Processing-Time"] = f"{processing_time_ms}ms"
        
        return JSONResponse(
            content=error_response.dict(),
            status_code=status_code,
            headers=headers
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        
        # Check common proxy headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in case of multiple proxies
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"


class CORSMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security considerations."""
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        allow_credentials: bool = False,
        max_age: int = 86400
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or [
            "Authorization",
            "Content-Type", 
            "X-Request-ID",
            "X-API-Key"
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS for requests."""
        
        if request.method == "OPTIONS":
            # Handle preflight requests
            return self._create_cors_preflight_response(request)
        
        # Process normal request
        response = await call_next(request)
        
        # Add CORS headers to response
        return self._add_cors_headers(request, response)

    def _create_cors_preflight_response(self, request: Request) -> Response:
        """Create response for CORS preflight requests."""
        
        response = Response()
        response.status_code = 200
        
        origin = request.headers.get("origin")
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response

    def _add_cors_headers(self, request: Request, response: Response) -> Response:
        """Add CORS headers to response."""
        
        origin = request.headers.get("origin")
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add exposed headers
        response.headers["Access-Control-Expose-Headers"] = ", ".join([
            "X-Request-ID",
            "X-Processing-Time",
            "X-API-Version"
        ])
        
        return response

    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""
        
        if not origin:
            return True
        
        if "*" in self.allow_origins:
            return True
        
        return origin in self.allow_origins


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy for API
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'none'; "
            "style-src 'none'; "
            "img-src 'none'; "
            "font-src 'none'; "
            "connect-src 'self'; "
            "base-uri 'none'"
        )
        
        # Strict Transport Security (HTTPS only)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(
        self, 
        app: ASGIApp,
        requests_per_minute: int = 100,
        burst_size: int = 20
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.clients = {}  # In production, use Redis or similar

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries (simple cleanup)
        if len(self.clients) > 10000:  # Prevent memory bloat
            cutoff_time = current_time - 3600  # Remove entries older than 1 hour
            self.clients = {
                ip: data for ip, data in self.clients.items() 
                if data['last_request'] > cutoff_time
            }
        
        # Get or create client data
        if client_ip not in self.clients:
            self.clients[client_ip] = {
                'requests': [],
                'last_request': current_time
            }
        
        client_data = self.clients[client_ip]
        
        # Remove requests older than 1 minute
        minute_ago = current_time - 60
        client_data['requests'] = [
            req_time for req_time in client_data['requests'] 
            if req_time > minute_ago
        ]
        
        # Check rate limit
        if len(client_data['requests']) >= self.requests_per_minute:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Rate limit exceeded",
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Maximum {self.requests_per_minute} requests per minute exceeded"
                    }
                },
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 60)),
                    "Retry-After": "60"
                }
            )
        
        # Record this request
        client_data['requests'].append(current_time)
        client_data['last_request'] = current_time
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(client_data['requests']))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        
        # Check common proxy headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"