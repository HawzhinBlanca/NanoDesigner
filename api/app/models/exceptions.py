"""Custom exception classes for the SGD API.

This module defines specific exception types for different error scenarios,
providing better error handling and more informative responses to clients.
"""

from typing import Dict, Any, Optional, List
from fastapi import HTTPException


class SGDBaseException(Exception):
    """Base exception for all SGD API errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class OpenRouterException(SGDBaseException):
    """Raised when OpenRouter API calls fail."""
    
    def __init__(self, 
                 message: str, 
                 status_code: Optional[int] = None,
                 model: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.model = model
        super().__init__(message, details)


class OpenRouterRateLimitException(OpenRouterException):
    """Raised when OpenRouter rate limits are exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None, model: Optional[str] = None):
        message = "OpenRouter API rate limit exceeded"
        details = {"retry_after_seconds": retry_after} if retry_after else {}
        super().__init__(message, status_code=429, model=model, details=details)


class OpenRouterModelUnavailableException(OpenRouterException):
    """Raised when requested model is unavailable."""
    
    def __init__(self, model: str, available_models: Optional[List[str]] = None):
        message = f"Model '{model}' is not available"
        details = {"available_models": available_models} if available_models else {}
        super().__init__(message, status_code=404, model=model, details=details)


class OpenRouterAuthenticationException(OpenRouterException):
    """Raised when OpenRouter authentication fails."""
    
    def __init__(self):
        message = "OpenRouter API authentication failed"
        super().__init__(message, status_code=401)


class GuardrailsValidationException(SGDBaseException):
    """Raised when Guardrails validation fails."""
    
    def __init__(self, contract_name: str, errors: List[str]):
        self.contract_name = contract_name
        self.validation_errors = errors
        message = f"Guardrails validation failed for {contract_name}"
        details = {"contract": contract_name, "validation_errors": errors}
        super().__init__(message, details)


class ContentPolicyViolationException(SGDBaseException):
    """Raised when content violates policy rules."""
    
    def __init__(self, violation_type: str, details: Optional[str] = None):
        self.violation_type = violation_type
        message = f"Content policy violation: {violation_type}"
        violation_details = {"violation_type": violation_type}
        if details:
            violation_details["details"] = details
        super().__init__(message, violation_details)


class ValidationError(SGDBaseException):
    """Raised when request validation fails."""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.value = value
        validation_message = f"Validation error for field '{field}': {message}"
        details = {"field": field, "message": message}
        if value is not None:
            details["value"] = value
        super().__init__(validation_message, details)


class ImageGenerationException(SGDBaseException):
    """Raised when image generation fails."""
    
    def __init__(self, 
                 message: str,
                 model: Optional[str] = None,
                 prompt_length: Optional[int] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.model = model
        self.prompt_length = prompt_length
        generation_details = details or {}
        if model:
            generation_details["model"] = model
        if prompt_length:
            generation_details["prompt_length"] = prompt_length
        super().__init__(message, generation_details)


class StorageException(SGDBaseException):
    """Raised when storage operations fail."""
    
    def __init__(self, 
                 operation: str,
                 key: Optional[str] = None,
                 storage_backend: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.key = key
        self.storage_backend = storage_backend
        message = f"Storage {operation} failed"
        storage_details = details or {}
        if key:
            storage_details["key"] = key
        if storage_backend:
            storage_details["backend"] = storage_backend
        super().__init__(message, storage_details)


class CacheException(SGDBaseException):
    """Raised when cache operations fail."""
    
    def __init__(self, 
                 operation: str,
                 key: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.key = key
        message = f"Cache {operation} failed"
        cache_details = details or {}
        if key:
            cache_details["key"] = key
        super().__init__(message, cache_details)


class QdrantException(SGDBaseException):
    """Raised when Qdrant operations fail."""
    
    def __init__(self, 
                 operation: str,
                 collection: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.collection = collection
        message = f"Qdrant {operation} failed"
        qdrant_details = details or {}
        if collection:
            qdrant_details["collection"] = collection
        super().__init__(message, qdrant_details)


class EmbeddingException(SGDBaseException):
    """Raised when embedding operations fail."""
    
    def __init__(self, 
                 message: str,
                 model: Optional[str] = None,
                 text_length: Optional[int] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.model = model
        self.text_length = text_length
        embedding_details = details or {}
        if model:
            embedding_details["model"] = model
        if text_length:
            embedding_details["text_length"] = text_length
        super().__init__(message, embedding_details)


class DocumentAIException(SGDBaseException):
    """Raised when Google Document AI operations fail."""
    
    def __init__(self, 
                 message: str,
                 processor_id: Optional[str] = None,
                 document_type: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.processor_id = processor_id
        self.document_type = document_type
        docai_details = details or {}
        if processor_id:
            docai_details["processor_id"] = processor_id
        if document_type:
            docai_details["document_type"] = document_type
        super().__init__(message, docai_details)


class JobException(SGDBaseException):
    """Raised when background job operations fail."""
    
    def __init__(self, 
                 message: str,
                 job_id: Optional[str] = None,
                 job_type: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.job_type = job_type
        job_details = details or {}
        if job_id:
            job_details["job_id"] = job_id
        if job_type:
            job_details["job_type"] = job_type
        super().__init__(message, job_details)


# HTTP Exception converters for FastAPI
def to_http_exception(exc: SGDBaseException, status_code: int = 500) -> HTTPException:
    """Convert custom exception to HTTPException for FastAPI."""
    detail = {
        "error": exc.__class__.__name__,
        "message": exc.message,
        **exc.details
    }
    return HTTPException(status_code=status_code, detail=detail)


def openrouter_to_http_exception(exc: OpenRouterException) -> HTTPException:
    """Convert OpenRouter exception to appropriate HTTP exception."""
    # Map OpenRouter status codes to appropriate HTTP status codes
    status_code_map = {
        401: 502,  # Auth errors become bad gateway
        403: 502,  # Forbidden becomes bad gateway  
        404: 502,  # Not found becomes bad gateway
        429: 429,  # Rate limit stays rate limit
        500: 502,  # Internal error becomes bad gateway
        502: 502,  # Bad gateway stays bad gateway
        503: 503,  # Service unavailable stays service unavailable
    }
    
    status_code = status_code_map.get(exc.status_code, 502)
    return to_http_exception(exc, status_code)


def guardrails_to_http_exception(exc: GuardrailsValidationException) -> HTTPException:
    """Convert Guardrails validation exception to HTTP 422."""
    detail = {
        "error": "ValidationError",
        "message": "Request validation failed",
        "guardrails": exc.validation_errors
    }
    return HTTPException(status_code=422, detail=detail)


def content_policy_to_http_exception(exc: ContentPolicyViolationException) -> HTTPException:
    """Convert content policy violation to HTTP 400."""
    return to_http_exception(exc, status_code=400)


def storage_to_http_exception(exc: StorageException) -> HTTPException:
    """Convert storage exception to HTTP 500."""
    return to_http_exception(exc, status_code=500)


def cache_to_http_exception(exc: CacheException) -> HTTPException:
    """Convert cache exception to HTTP 500."""
    return to_http_exception(exc, status_code=500)


# Exception handler registry
EXCEPTION_HANDLERS = {
    OpenRouterException: openrouter_to_http_exception,
    GuardrailsValidationException: guardrails_to_http_exception,
    ContentPolicyViolationException: content_policy_to_http_exception,
    StorageException: storage_to_http_exception,
    CacheException: cache_to_http_exception,
}