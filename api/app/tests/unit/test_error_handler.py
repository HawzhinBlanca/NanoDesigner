"""Unit tests for enhanced error handling service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi import HTTPException

from app.services.error_handler import (
    ErrorContext,
    ErrorHandler,
    get_error_handler,
    handle_errors,
    validate_input,
    safe_json_parse,
    retry_with_backoff
)
from app.models.exceptions import (
    OpenRouterException,
    ContentPolicyViolationException,
    ValidationError,
    StorageException
)


class TestErrorContext:
    """Test cases for ErrorContext class."""

    def test_error_context_creation(self):
        """Test ErrorContext creation and attributes."""
        context = ErrorContext(
            operation="test_operation",
            user_id="user123",
            project_id="project456",
            trace_id="trace789",
            request_id="req123"
        )
        
        assert context.operation == "test_operation"
        assert context.user_id == "user123"
        assert context.project_id == "project456"
        assert context.trace_id == "trace789"
        assert context.request_id == "req123"
        assert isinstance(context.timestamp, datetime)

    def test_error_context_to_dict(self):
        """Test ErrorContext to_dict conversion."""
        context = ErrorContext(
            operation="test_operation",
            user_id="user123",
            trace_id="trace789"
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["operation"] == "test_operation"
        assert context_dict["user_id"] == "user123"
        assert context_dict["trace_id"] == "trace789"
        assert context_dict["project_id"] is None
        assert "timestamp" in context_dict

    def test_error_context_minimal(self):
        """Test ErrorContext with minimal parameters."""
        context = ErrorContext("minimal_op")
        
        assert context.operation == "minimal_op"
        assert context.user_id is None
        assert context.project_id is None
        assert context.trace_id is None
        assert context.request_id is None


class TestErrorHandler:
    """Test cases for ErrorHandler class."""

    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        
        assert isinstance(handler.error_counts, dict)
        assert isinstance(handler.circuit_breakers, dict)
        assert len(handler.error_counts) == 0
        assert len(handler.circuit_breakers) == 0

    def test_handle_openrouter_exception(self):
        """Test handling OpenRouter exceptions."""
        handler = ErrorHandler()
        context = ErrorContext("test_operation", trace_id="trace123")
        
        exc = OpenRouterException(
            message="Model unavailable",
            status_code=503,
            model="gpt-4"
        )
        
        result = handler.handle_exception(exc, context)
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 503
        assert "OpenRouterException" in result.detail["error"]

    def test_handle_content_policy_exception(self):
        """Test handling content policy violations."""
        handler = ErrorHandler()
        context = ErrorContext("content_check")
        
        exc = ContentPolicyViolationException(
            violation_type="banned_term",
            details="Contains inappropriate content"
        )
        
        result = handler.handle_exception(exc, context)
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 400
        assert "ContentPolicyViolationException" in result.detail["error"]

    def test_handle_validation_error(self):
        """Test handling validation errors."""
        handler = ErrorHandler()
        context = ErrorContext("validation")
        
        exc = ValidationError(
            field="test_field",
            message="Invalid value",
            value="bad_value"
        )
        
        result = handler.handle_exception(exc, context)
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 500  # Default for unhandled SGD exceptions
        assert "ValidationError" in result.detail["error"]

    def test_handle_unknown_exception(self):
        """Test handling unknown exceptions."""
        handler = ErrorHandler()
        context = ErrorContext("unknown_op", trace_id="trace456")
        
        exc = ValueError("Something went wrong")
        
        result = handler.handle_exception(exc, context)
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 500
        assert result.detail["error"] == "InternalServerError"
        assert result.detail["trace_id"] == "trace456"

    def test_handle_unknown_exception_with_fallback(self):
        """Test handling unknown exceptions with fallback response."""
        handler = ErrorHandler()
        context = ErrorContext("fallback_op")
        
        exc = RuntimeError("Unexpected error")
        fallback = {"status": "degraded", "data": "fallback_data"}
        
        result = handler.handle_exception(exc, context, fallback)
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 200
        assert result.detail["status"] == "partial_success"
        assert result.detail["data"] == fallback

    def test_circuit_breaker_logic(self):
        """Test circuit breaker activation."""
        handler = ErrorHandler()
        context = ErrorContext("failing_service")
        
        # Simulate multiple failures
        exc = OpenRouterException("Service down", status_code=503)
        
        for i in range(12):  # Exceed threshold of 10
            handler.handle_exception(exc, context)
        
        assert handler.is_circuit_breaker_open("failing_service")

    def test_circuit_breaker_reset(self):
        """Test circuit breaker reset functionality."""
        handler = ErrorHandler()
        
        # Activate circuit breaker
        handler.circuit_breakers["test_service"] = True
        assert handler.is_circuit_breaker_open("test_service")
        
        # Reset circuit breaker
        handler.reset_circuit_breaker("test_service")
        assert not handler.is_circuit_breaker_open("test_service")


class TestGlobalFunctions:
    """Test cases for global utility functions."""

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2
        assert isinstance(handler1, ErrorHandler)

    def test_validate_input_success(self):
        """Test successful input validation."""
        def is_positive(x):
            return x > 0
        
        def is_integer(x):
            return isinstance(x, int)
        
        # Should not raise any exception
        validate_input(
            5,
            "test_field",
            [is_positive, is_integer],
            ["Must be positive", "Must be integer"]
        )

    def test_validate_input_failure(self):
        """Test input validation failure."""
        def is_positive(x):
            return x > 0
        
        with pytest.raises(ValidationError) as exc_info:
            validate_input(
                -5,
                "test_field",
                [is_positive],
                ["Must be positive"]
            )
        
        assert exc_info.value.field == "test_field"
        assert "Must be positive" in exc_info.value.message

    def test_safe_json_parse_success(self):
        """Test successful JSON parsing."""
        json_str = '{"key": "value", "number": 42}'
        
        result = safe_json_parse(json_str, "test_json")
        
        assert result == {"key": "value", "number": 42}

    def test_safe_json_parse_failure_with_fallback(self):
        """Test JSON parsing failure with fallback."""
        invalid_json = '{"invalid": json}'
        fallback = {"fallback": "data"}
        
        result = safe_json_parse(invalid_json, "test_json", fallback)
        
        assert result == fallback

    def test_safe_json_parse_failure_without_fallback(self):
        """Test JSON parsing failure without fallback."""
        invalid_json = '{"invalid": json}'
        
        with pytest.raises(ValidationError) as exc_info:
            safe_json_parse(invalid_json, "test_json")
        
        assert exc_info.value.field == "test_json"
        assert "Invalid JSON format" in exc_info.value.message


class TestHandleErrorsDecorator:
    """Test cases for handle_errors decorator."""

    @pytest.mark.asyncio
    async def test_handle_errors_success(self):
        """Test handle_errors decorator with successful function."""
        @handle_errors("test_operation")
        async def successful_function():
            return {"success": True}
        
        result = await successful_function()
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_handle_errors_with_exception(self):
        """Test handle_errors decorator with exception."""
        @handle_errors("test_operation")
        async def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(HTTPException) as exc_info:
            await failing_function()
        
        assert exc_info.value.status_code == 500
        assert "InternalServerError" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_handle_errors_with_fallback(self):
        """Test handle_errors decorator with fallback response."""
        fallback = {"fallback": "response"}
        
        @handle_errors("test_operation", fallback_response=fallback)
        async def failing_function():
            raise RuntimeError("Test error")
        
        with pytest.raises(HTTPException) as exc_info:
            await failing_function()
        
        # Should return fallback as partial success
        assert exc_info.value.status_code == 200
        assert exc_info.value.detail["status"] == "partial_success"

    @pytest.mark.asyncio
    async def test_handle_errors_circuit_breaker(self):
        """Test handle_errors decorator with circuit breaker."""
        # Mock circuit breaker as open
        with patch('app.services.error_handler.get_error_handler') as mock_get_handler:
            mock_handler = Mock()
            mock_handler.is_circuit_breaker_open.return_value = True
            mock_get_handler.return_value = mock_handler
            
            @handle_errors("blocked_operation")
            async def blocked_function():
                return {"should": "not_execute"}
            
            with pytest.raises(HTTPException) as exc_info:
                await blocked_function()
            
            assert exc_info.value.status_code == 503
            assert "ServiceUnavailable" in exc_info.value.detail["error"]


class TestRetryDecorator:
    """Test cases for retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test retry decorator with successful first attempt."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return {"attempt": call_count}
        
        result = await successful_function()
        
        assert result == {"attempt": 1}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test retry decorator with success after failures."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)  # Fast for testing
        async def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return {"attempt": call_count}
        
        result = await eventually_successful_function()
        
        assert result == {"attempt": 3}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry decorator with all attempts exhausted."""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise RuntimeError(f"Failure {call_count}")
        
        with pytest.raises(RuntimeError) as exc_info:
            await always_failing_function()
        
        assert "Failure 3" in str(exc_info.value)  # 1 + 2 retries
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_no_retry_on_validation_error(self):
        """Test that certain errors are not retried."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        async def validation_error_function():
            nonlocal call_count
            call_count += 1
            raise ValidationError("field", "Invalid", "value")
        
        with pytest.raises(ValidationError):
            await validation_error_function()
        
        # Should not retry validation errors
        assert call_count == 1
