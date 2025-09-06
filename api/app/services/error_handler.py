"""Enhanced error handling service for comprehensive error management.

This module provides utilities for robust error handling, logging, and recovery
across all API endpoints and services.
"""

from __future__ import annotations

import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from datetime import datetime

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.exceptions import (
    SGDBaseException,
    OpenRouterException,
    GuardrailsValidationException,
    ContentPolicyViolationException,
    StorageException,
    CacheException,
    ValidationError,
    ImageGenerationException,
    EXCEPTION_HANDLERS
)

logger = logging.getLogger(__name__)


class ErrorContext:
    """Context information for error handling."""
    
    def __init__(self, 
                 operation: str,
                 user_id: Optional[str] = None,
                 project_id: Optional[str] = None,
                 trace_id: Optional[str] = None,
                 request_id: Optional[str] = None):
        self.operation = operation
        self.user_id = user_id
        self.project_id = project_id
        self.trace_id = trace_id
        self.request_id = request_id
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "operation": self.operation,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat()
        }


class ErrorHandler:
    """Centralized error handling service."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.circuit_breakers: Dict[str, bool] = {}
    
    def handle_exception(self, 
                        exc: Exception, 
                        context: ErrorContext,
                        fallback_response: Optional[Dict[str, Any]] = None) -> HTTPException:
        """Handle any exception and convert to appropriate HTTP response.
        
        Args:
            exc: The exception to handle
            context: Error context information
            fallback_response: Optional fallback response for graceful degradation
            
        Returns:
            HTTPException: Appropriate HTTP exception
        """
        # Log the error with full context
        self._log_error(exc, context)
        
        # Update error metrics
        self._update_error_metrics(exc, context)
        
        # Handle known exception types
        if isinstance(exc, SGDBaseException):
            return self._handle_sgd_exception(exc, context)
        
        # Handle HTTP exceptions
        if isinstance(exc, HTTPException):
            return exc
        
        # Handle unknown exceptions
        return self._handle_unknown_exception(exc, context, fallback_response)
    
    def _log_error(self, exc: Exception, context: ErrorContext) -> None:
        """Log error with comprehensive context."""
        error_data = {
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "context": context.to_dict(),
            "traceback": traceback.format_exc()
        }
        
        # Log at appropriate level based on error type
        if isinstance(exc, (ContentPolicyViolationException, ValidationError)):
            logger.warning("User error occurred", extra=error_data)
        elif isinstance(exc, (OpenRouterException, StorageException)):
            logger.error("Service error occurred", extra=error_data)
        else:
            logger.exception("Unexpected error occurred", extra=error_data)
    
    def _update_error_metrics(self, exc: Exception, context: ErrorContext) -> None:
        """Update error metrics for monitoring."""
        error_key = f"{context.operation}:{exc.__class__.__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Implement circuit breaker logic for critical services
        if isinstance(exc, OpenRouterException) and self.error_counts[error_key] > 10:
            self.circuit_breakers[context.operation] = True
            logger.critical(f"Circuit breaker activated for {context.operation}")
    
    def _handle_sgd_exception(self, exc: SGDBaseException, context: ErrorContext) -> HTTPException:
        """Handle known SGD exceptions."""
        handler = EXCEPTION_HANDLERS.get(type(exc))
        if handler:
            return handler(exc)
        
        # Fallback for unhandled SGD exceptions
        return HTTPException(
            status_code=500,
            detail={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "trace_id": context.trace_id,
                **exc.details
            }
        )
    
    def _handle_unknown_exception(self, 
                                 exc: Exception, 
                                 context: ErrorContext,
                                 fallback_response: Optional[Dict[str, Any]]) -> HTTPException:
        """Handle unknown exceptions with graceful degradation."""
        if fallback_response:
            logger.info(f"Using fallback response for {context.operation}")
            return HTTPException(
                status_code=200,
                detail={
                    "status": "partial_success",
                    "message": "Request completed with degraded functionality",
                    "data": fallback_response,
                    "trace_id": context.trace_id
                }
            )
        
        # Generic error response
        return HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "trace_id": context.trace_id,
                "error_id": f"{context.operation}_{context.timestamp.timestamp()}"
            }
        )
    
    def is_circuit_breaker_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for an operation."""
        return self.circuit_breakers.get(operation, False)
    
    def reset_circuit_breaker(self, operation: str) -> None:
        """Reset circuit breaker for an operation."""
        self.circuit_breakers[operation] = False
        logger.info(f"Circuit breaker reset for {operation}")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_errors(operation: str, 
                 fallback_response: Optional[Dict[str, Any]] = None):
    """Decorator for comprehensive error handling.
    
    Args:
        operation: Name of the operation being performed
        fallback_response: Optional fallback response for graceful degradation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            handler = get_error_handler()
            
            # Extract context from request if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            context = ErrorContext(
                operation=operation,
                trace_id=getattr(request, 'trace_id', None) if request else None,
                request_id=getattr(request, 'request_id', None) if request else None
            )
            
            # Check circuit breaker
            if handler.is_circuit_breaker_open(operation):
                logger.warning(f"Circuit breaker open for {operation}, using fallback")
                if fallback_response:
                    return fallback_response
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "ServiceUnavailable",
                        "message": f"Service {operation} is temporarily unavailable"
                    }
                )
            
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                raise handler.handle_exception(exc, context, fallback_response)
        
        return wrapper
    return decorator


def validate_input(data: Any, 
                  field_name: str, 
                  validators: List[Callable[[Any], bool]],
                  error_messages: List[str]) -> None:
    """Validate input data with custom validators.
    
    Args:
        data: Data to validate
        field_name: Name of the field being validated
        validators: List of validation functions
        error_messages: Corresponding error messages
        
    Raises:
        ValidationError: If validation fails
    """
    for validator, message in zip(validators, error_messages):
        if not validator(data):
            raise ValidationError(field_name, message, data)


def safe_json_parse(json_str: str, 
                   field_name: str = "json_data",
                   fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Safely parse JSON with error handling.
    
    Args:
        json_str: JSON string to parse
        field_name: Name of the field for error reporting
        fallback: Fallback value if parsing fails
        
    Returns:
        Dict: Parsed JSON data or fallback
        
    Raises:
        ValidationError: If parsing fails and no fallback provided
    """
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        if fallback is not None:
            logger.warning(f"JSON parsing failed for {field_name}, using fallback: {e}")
            return fallback
        
        raise ValidationError(
            field_name,
            f"Invalid JSON format: {str(e)}",
            json_str[:100] + "..." if len(json_str) > 100 else json_str
        )


def retry_with_backoff(max_retries: int = 3, 
                      base_delay: float = 1.0,
                      max_delay: float = 60.0,
                      exponential_base: float = 2.0):
    """Decorator for retrying operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    
                    # Don't retry on certain error types
                    if isinstance(exc, (ContentPolicyViolationException, ValidationError)):
                        raise
                    
                    if attempt == max_retries:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {exc}")
                    await asyncio.sleep(delay)
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator
