"""Standardized response models for consistent API responses.

This module defines standardized response formats that ensure consistency
across all API endpoints, improve client experience, and provide comprehensive
metadata for debugging and monitoring.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid

T = TypeVar('T')

class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PENDING = "pending"

class ResponseMeta(BaseModel):
    """Metadata included in all API responses."""
    
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="ISO timestamp when response was generated"
    )
    version: str = Field(
        default="1.0.0",
        description="API version that generated this response"
    )
    processing_time_ms: Optional[int] = Field(
        None,
        description="Time taken to process request in milliseconds"
    )
    
class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    
    total: int = Field(
        description="Total number of items available"
    )
    count: int = Field(
        description="Number of items in current page"
    )
    page: int = Field(
        default=1,
        description="Current page number (1-based)"
    )
    per_page: int = Field(
        default=20,
        description="Items per page"
    )
    pages: int = Field(
        description="Total number of pages"
    )
    has_next: bool = Field(
        description="Whether there is a next page"
    )
    has_prev: bool = Field(
        description="Whether there is a previous page"
    )
    next_url: Optional[str] = Field(
        None,
        description="URL for next page"
    )
    prev_url: Optional[str] = Field(
        None, 
        description="URL for previous page"
    )

class StandardResponse(BaseModel, Generic[T]):
    """Base response model for all API endpoints."""
    
    status: ResponseStatus = Field(
        description="Response status indicator"
    )
    message: str = Field(
        description="Human-readable response message"
    )
    data: Optional[T] = Field(
        None,
        description="Response data payload"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ListResponse(BaseModel, Generic[T]):
    """Standardized response for paginated list endpoints."""
    
    status: ResponseStatus = Field(
        description="Response status indicator" 
    )
    message: str = Field(
        description="Human-readable response message"
    )
    data: List[T] = Field(
        description="Array of response items"
    )
    pagination: PaginationMeta = Field(
        description="Pagination metadata"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )
    
    class Config:
        use_enum_values = True

class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    code: str = Field(
        description="Error code for programmatic handling"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    field: Optional[str] = Field(
        None,
        description="Field name if this is a validation error"
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )

class ErrorResponse(BaseModel):
    """Standardized error response format."""
    
    status: ResponseStatus = Field(
        default=ResponseStatus.ERROR,
        description="Response status (always 'error')"
    )
    message: str = Field(
        description="Main error message"
    )
    error: ErrorDetail = Field(
        description="Detailed error information"
    )
    errors: Optional[List[ErrorDetail]] = Field(
        None,
        description="Multiple errors (e.g., validation errors)"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )
    
    class Config:
        use_enum_values = True

class HealthResponse(BaseModel):
    """Health check response format."""
    
    status: ResponseStatus = Field(
        description="Overall health status"
    )
    message: str = Field(
        description="Health status message"
    )
    data: Dict[str, Any] = Field(
        description="Health check details"
    )
    checks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Individual service health checks"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "status": "success",
                "message": "System is healthy",
                "data": {
                    "uptime_seconds": 3600,
                    "version": "1.0.0",
                    "environment": "production"
                },
                "checks": {
                    "database": {
                        "status": "healthy",
                        "response_time_ms": 45,
                        "details": "Connection pool: 5/20 active"
                    },
                    "redis": {
                        "status": "healthy", 
                        "response_time_ms": 12,
                        "details": "Memory usage: 125MB"
                    },
                    "external_apis": {
                        "status": "healthy",
                        "details": {
                            "openrouter": "operational",
                            "storage": "operational"
                        }
                    }
                },
                "meta": {
                    "request_id": "req_123456",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "version": "1.0.0",
                    "processing_time_ms": 85
                }
            }
        }

class JobStatus(str, Enum):
    """Job processing status values."""
    QUEUED = "queued"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobResponse(BaseModel):
    """Response for async job operations."""
    
    status: ResponseStatus = Field(
        description="Response status"
    )
    message: str = Field(
        description="Job status message"
    )
    data: Dict[str, Any] = Field(
        description="Job details"
    )
    job: Dict[str, Any] = Field(
        description="Job metadata"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Job submitted successfully",
                "data": {
                    "preview_url": "https://cdn.example.com/preview/123.png",
                    "progress": 75,
                    "estimated_completion": "2024-01-01T12:05:00Z"
                },
                "job": {
                    "id": "job_abc123",
                    "status": "processing",
                    "created_at": "2024-01-01T12:00:00Z",
                    "updated_at": "2024-01-01T12:03:45Z",
                    "type": "render",
                    "priority": "normal"
                },
                "meta": {
                    "request_id": "req_789012", 
                    "timestamp": "2024-01-01T12:03:45Z",
                    "version": "1.0.0",
                    "processing_time_ms": 150
                }
            }
        }

class ValidationErrorDetail(ErrorDetail):
    """Enhanced error detail for validation errors."""
    
    field: str = Field(
        description="Field that failed validation"
    )
    value: Any = Field(
        description="Value that was rejected"
    )
    constraint: str = Field(
        description="Validation constraint that was violated"
    )
    
class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation failures."""
    
    errors: List[ValidationErrorDetail] = Field(
        description="List of validation errors"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "Request validation failed",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "One or more fields failed validation",
                    "context": {
                        "total_errors": 2
                    }
                },
                "errors": [
                    {
                        "code": "VALUE_TOO_SHORT",
                        "message": "Instruction must be at least 5 characters",
                        "field": "prompts.instruction",
                        "value": "Hi",
                        "constraint": "min_length=5"
                    },
                    {
                        "code": "INVALID_FORMAT",
                        "message": "Invalid hex color format",
                        "field": "constraints.palette_hex[0]",
                        "value": "red",
                        "constraint": "pattern=#[0-9A-Fa-f]{6}"
                    }
                ],
                "meta": {
                    "request_id": "req_345678",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "version": "1.0.0",
                    "processing_time_ms": 25
                }
            }
        }

class MetricsResponse(BaseModel):
    """Response for metrics endpoint."""
    
    status: ResponseStatus = Field(
        description="Response status"
    )
    message: str = Field(
        description="Metrics collection message"
    )
    data: Dict[str, Any] = Field(
        description="Metrics data"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Metrics collected successfully",
                "data": {
                    "requests": {
                        "total": 15420,
                        "successful": 14891,
                        "failed": 529,
                        "rate_limited": 0
                    },
                    "performance": {
                        "avg_response_time_ms": 245,
                        "p95_response_time_ms": 850,
                        "p99_response_time_ms": 1200
                    },
                    "resources": {
                        "cpu_usage_percent": 45,
                        "memory_usage_mb": 512,
                        "disk_usage_percent": 12
                    },
                    "business": {
                        "renders_completed": 1205,
                        "cost_usd": 127.45,
                        "active_projects": 89
                    }
                },
                "meta": {
                    "request_id": "req_metrics_001",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "version": "1.0.0",
                    "processing_time_ms": 15
                }
            }
        }

# Response factory functions for consistent response creation

def create_success_response(
    data: Any = None,
    message: str = "Request completed successfully",
    request_id: Optional[str] = None,
    processing_time_ms: Optional[int] = None
) -> StandardResponse:
    """Create a standardized success response."""
    
    meta = ResponseMeta()
    if request_id:
        meta.request_id = request_id
    if processing_time_ms is not None:
        meta.processing_time_ms = processing_time_ms
        
    return StandardResponse(
        status=ResponseStatus.SUCCESS,
        message=message,
        data=data,
        meta=meta
    )

def create_error_response(
    message: str,
    error_code: str,
    error_message: Optional[str] = None,
    field: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    processing_time_ms: Optional[int] = None
) -> ErrorResponse:
    """Create a standardized error response."""
    
    meta = ResponseMeta()
    if request_id:
        meta.request_id = request_id
    if processing_time_ms is not None:
        meta.processing_time_ms = processing_time_ms
    
    return ErrorResponse(
        status=ResponseStatus.ERROR,
        message=message,
        error=ErrorDetail(
            code=error_code,
            message=error_message or message,
            field=field,
            context=context
        ),
        meta=meta
    )

def create_validation_error_response(
    errors: List[Dict[str, Any]],
    message: str = "Request validation failed",
    request_id: Optional[str] = None,
    processing_time_ms: Optional[int] = None
) -> ValidationErrorResponse:
    """Create a standardized validation error response."""
    
    meta = ResponseMeta()
    if request_id:
        meta.request_id = request_id
    if processing_time_ms is not None:
        meta.processing_time_ms = processing_time_ms
    
    validation_errors = []
    for error in errors:
        validation_errors.append(ValidationErrorDetail(
            code=error.get('code', 'VALIDATION_ERROR'),
            message=error.get('message', 'Validation failed'),
            field=error.get('field', ''),
            value=error.get('value'),
            constraint=error.get('constraint', '')
        ))
    
    return ValidationErrorResponse(
        status=ResponseStatus.ERROR,
        message=message,
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="One or more fields failed validation",
            context={"total_errors": len(errors)}
        ),
        errors=validation_errors,
        meta=meta
    )

def create_list_response(
    items: List[Any],
    total: int,
    page: int = 1,
    per_page: int = 20,
    message: str = "Items retrieved successfully",
    request_id: Optional[str] = None,
    processing_time_ms: Optional[int] = None
) -> ListResponse:
    """Create a standardized paginated list response."""
    
    meta = ResponseMeta()
    if request_id:
        meta.request_id = request_id
    if processing_time_ms is not None:
        meta.processing_time_ms = processing_time_ms
    
    pages = (total + per_page - 1) // per_page  # Ceiling division
    
    pagination = PaginationMeta(
        total=total,
        count=len(items),
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )
    
    return ListResponse(
        status=ResponseStatus.SUCCESS,
        message=message,
        data=items,
        pagination=pagination,
        meta=meta
    )

def create_job_response(
    job_id: str,
    job_status: JobStatus,
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    request_id: Optional[str] = None,
    processing_time_ms: Optional[int] = None
) -> JobResponse:
    """Create a standardized job response."""
    
    meta = ResponseMeta()
    if request_id:
        meta.request_id = request_id
    if processing_time_ms is not None:
        meta.processing_time_ms = processing_time_ms
    
    if not message:
        message = f"Job {job_status.value}"
    
    job_info = {
        "id": job_id,
        "status": job_status.value,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return JobResponse(
        status=ResponseStatus.SUCCESS,
        message=message,
        data=data or {},
        job=job_info,
        meta=meta
    )