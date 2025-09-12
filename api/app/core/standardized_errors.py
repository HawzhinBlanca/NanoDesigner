"""Standardized error response system for consistent API responses."""

from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
import uuid
import time


class StandardError:
    """Standard error response format for all API endpoints."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.trace_id = trace_id or str(uuid.uuid4())
        self.timestamp = int(time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        response = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "trace_id": self.trace_id,
                "timestamp": self.timestamp
            }
        }
        
        if self.details:
            response["error"]["details"] = self.details
            
        return response
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict()
        )
    
    def to_json_response(self) -> JSONResponse:
        """Convert to FastAPI JSONResponse."""
        return JSONResponse(
            status_code=self.status_code,
            content=self.to_dict()
        )


# Standard error codes and factories
class StandardErrors:
    """Factory for common standardized errors."""
    
    @staticmethod
    def validation_error(message: str, field: str = None, trace_id: str = None) -> StandardError:
        """Validation error (400)."""
        details = {"field": field} if field else {}
        return StandardError(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            trace_id=trace_id
        )
    
    @staticmethod
    def authentication_error(message: str = "Authentication required", trace_id: str = None) -> StandardError:
        """Authentication error (401)."""
        return StandardError(
            error_code="AUTHENTICATION_ERROR",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            trace_id=trace_id
        )
    
    @staticmethod
    def authorization_error(message: str = "Insufficient permissions", trace_id: str = None) -> StandardError:
        """Authorization error (403)."""
        return StandardError(
            error_code="AUTHORIZATION_ERROR",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            trace_id=trace_id
        )
    
    @staticmethod
    def not_found_error(resource: str = "Resource", trace_id: str = None) -> StandardError:
        """Not found error (404)."""
        return StandardError(
            error_code="NOT_FOUND",
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            trace_id=trace_id
        )
    
    @staticmethod
    def rate_limit_error(retry_after: int = 60, trace_id: str = None) -> StandardError:
        """Rate limit error (429)."""
        return StandardError(
            error_code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after},
            trace_id=trace_id
        )
    
    @staticmethod
    def internal_error(message: str = "Internal server error", trace_id: str = None) -> StandardError:
        """Internal server error (500)."""
        return StandardError(
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            trace_id=trace_id
        )
    
    @staticmethod
    def service_unavailable_error(service: str = "Service", trace_id: str = None) -> StandardError:
        """Service unavailable error (503)."""
        return StandardError(
            error_code="SERVICE_UNAVAILABLE",
            message=f"{service} is temporarily unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            trace_id=trace_id
        )
    
    @staticmethod
    def security_policy_error(violation_type: str, details: str = None, trace_id: str = None) -> StandardError:
        """Security policy violation error (400)."""
        return StandardError(
            error_code="SECURITY_POLICY_VIOLATION",
            message=f"Security policy violation: {violation_type}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"violation_type": violation_type, "details": details},
            trace_id=trace_id
        )
    
    @staticmethod
    def ai_model_error(model: str, error_details: str = None, trace_id: str = None) -> StandardError:
        """AI model error (502)."""
        return StandardError(
            error_code="AI_MODEL_ERROR",
            message=f"AI model '{model}' error",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"model": model, "error_details": error_details},
            trace_id=trace_id
        )


def standardize_http_exception(exc: HTTPException, trace_id: str = None) -> JSONResponse:
    """Convert any HTTPException to standardized format."""
    
    # If it's already in standard format, return as-is
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    
    # Convert to standard format
    error_code_map = {
        400: "VALIDATION_ERROR",
        401: "AUTHENTICATION_ERROR", 
        403: "AUTHORIZATION_ERROR",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE"
    }
    
    error_code = error_code_map.get(exc.status_code, "UNKNOWN_ERROR")
    message = str(exc.detail) if exc.detail else "An error occurred"
    
    standard_error = StandardError(
        error_code=error_code,
        message=message,
        status_code=exc.status_code,
        trace_id=trace_id
    )
    
    return standard_error.to_json_response()





