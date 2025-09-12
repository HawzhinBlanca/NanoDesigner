"""
Production-ready middleware for security, tracking, and performance
"""
import uuid
import time
import logging
from typing import Optional
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests for tracing"""
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        
        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        
        # HSTS for production
        if os.getenv("SERVICE_ENV") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # CSP header
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Get current time
        now = time.time()
        
        # Clean old entries
        self.clients = {
            k: v for k, v in self.clients.items()
            if now - v["first_request"] < self.period
        }
        
        # Check rate limit
        if client_id in self.clients:
            client_data = self.clients[client_id]
            if client_data["requests"] >= self.calls:
                remaining = self.period - (now - client_data["first_request"])
                
                response = Response(
                    content="Rate limit exceeded",
                    status_code=429,
                    headers={
                        "Retry-After": str(int(remaining)),
                        "X-RateLimit-Limit": str(self.calls),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + remaining))
                    }
                )
                return response
            
            client_data["requests"] += 1
        else:
            self.clients[client_id] = {
                "requests": 1,
                "first_request": now
            }
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        client_data = self.clients.get(client_id, {})
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.calls - client_data.get("requests", 0))
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(client_data.get("first_request", now) + self.period)
        )
        
        return response

class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request metrics"""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Update metrics
            self.request_count += 1
            if response.status_code >= 500:
                self.error_count += 1
            
            response_time = time.time() - start_time
            self.total_response_time += response_time
            
            # Add metrics to response headers (for debugging)
            if request.url.path == "/metrics/json":
                response.headers["X-Total-Requests"] = str(self.request_count)
                response.headers["X-Error-Rate"] = str(
                    self.error_count / max(1, self.request_count)
                )
                response.headers["X-Avg-Response-Time"] = str(
                    self.total_response_time / max(1, self.request_count)
                )
            
            return response
            
        except Exception as e:
            self.error_count += 1
            raise

def setup_middleware(app):
    """Configure all production middleware"""
    
    # Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-*"]
    )
    
    # Trusted hosts
    if os.getenv("ALLOWED_HOSTS"):
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=os.getenv("ALLOWED_HOSTS").split(",")
        )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request ID tracking
    app.add_middleware(RequestIDMiddleware)
    
    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        calls=int(os.getenv("RATE_LIMIT_PER_MINUTE", 100)),
        period=60
    )
    
    # Metrics collection
    app.add_middleware(MetricsMiddleware)
    
    logger.info("Production middleware configured")