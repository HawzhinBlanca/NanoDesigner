"""Request size limiting middleware for production safety."""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size and prevent DoS attacks.
    
    This middleware checks the Content-Length header and rejects requests
    that exceed the configured maximum size before reading the body.
    """
    
    def __init__(self, app: ASGIApp, max_size: int = 10485760):  # 10MB default
        """Initialize the middleware.
        
        Args:
            app: The ASGI application
            max_size: Maximum allowed request size in bytes (default 10MB)
        """
        super().__init__(app)
        self.max_size = max_size
        self.max_size_mb = max_size / (1024 * 1024)
    
    async def dispatch(self, request: Request, call_next):
        """Check request size before processing.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response from the next handler or error if size exceeded
        """
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        f"Request size {size} bytes exceeds limit {self.max_size} bytes",
                        extra={
                            "request_id": getattr(request.state, 'request_id', 'unknown'),
                            "content_length": size,
                            "max_size": self.max_size,
                            "client": request.client.host if request.client else "unknown"
                        }
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PayloadTooLarge",
                            "message": f"Request body too large. Maximum size is {self.max_size_mb:.1f}MB",
                            "max_size_bytes": self.max_size
                        }
                    )
            except (ValueError, TypeError):
                # Invalid Content-Length header
                logger.warning(
                    f"Invalid Content-Length header: {content_length}",
                    extra={"request_id": getattr(request.state, 'request_id', 'unknown')}
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "InvalidRequest",
                        "message": "Invalid Content-Length header"
                    }
                )
        
        # For chunked transfer encoding or missing Content-Length,
        # we would need to implement streaming size check which is more complex
        # For now, proceed with the request but log a warning for monitoring
        if not content_length and request.method in ["POST", "PUT", "PATCH"]:
            logger.info(
                "Request without Content-Length header",
                extra={
                    "request_id": getattr(request.state, 'request_id', 'unknown'),
                    "method": request.method,
                    "path": request.url.path
                }
            )
        
        # Process the request
        response = await call_next(request)
        return response