"""Enhanced structured logging with security sanitization.

This module provides structured logging with JSON output for better
observability and log aggregation in production environments.
Includes security sanitization to prevent sensitive data leakage.
"""

import logging
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

from .config import settings

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class SecuritySanitizer:
    """Sanitize sensitive information from logs."""
    
    # Patterns to detect and redact sensitive information
    SENSITIVE_PATTERNS = {
        'api_key': re.compile(r'(api[_-]?key["\s:=]+["\']?)([a-zA-Z0-9_-]{20,})', re.IGNORECASE),
        'bearer_token': re.compile(r'(bearer\s+)([a-zA-Z0-9_.-]{20,})', re.IGNORECASE),
        'password': re.compile(r'(password["\s:=]+["\']?)([^\s"\']{{4,}})', re.IGNORECASE),
        'secret': re.compile(r'(secret["\s:=]+["\']?)([a-zA-Z0-9_.-]{20,})', re.IGNORECASE),
        'authorization': re.compile(r'(authorization["\s:=]+["\']?)([a-zA-Z0-9_.-]{20,})', re.IGNORECASE),
        'jwt': re.compile(r'(eyJ[a-zA-Z0-9_.-]+)', re.IGNORECASE),  # JWT tokens
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{{2,}}\b'),
        'credit_card': re.compile(r'\b(?:\d{{4}}[-\s]?){{3}}\d{{4}}\b'),
        'ssn': re.compile(r'\b\d{{3}}-\d{{2}}-\d{{4}}\b'),
        'phone': re.compile(r'\b\+?1?[-\.\s]?\(?[0-9]{{3}}\)?[-\.\s]?[0-9]{{3}}[-\.\s]?[0-9]{{4}}\b'),
    }
    
    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Sanitize a string by redacting sensitive information."""
        if not isinstance(text, str):
            return str(text)
        
        sanitized = text
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            # Replace with first group + redacted indicator
            sanitized = pattern.sub(r'\1***REDACTED***', sanitized)
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
        """Recursively sanitize a dictionary."""
        if max_depth <= 0:
            return {{"...": "max_depth_reached"}}
        
        sanitized = {{}}
        for key, value in data.items():
            # Check if key itself is sensitive
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in ['password', 'secret', 'token', 'key', 'auth']):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value, max_depth - 1)
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def sanitize_list(cls, data: List[Any], max_depth: int = 3) -> List[Any]:
        """Sanitize a list by sanitizing its elements."""
        if max_depth <= 0:
            return ["...max_depth_reached"]
        
        sanitized = []
        for item in data[:10]:  # Limit list length in logs
            if isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, max_depth - 1))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, max_depth - 1))
            elif isinstance(item, str):
                sanitized.append(cls.sanitize_string(item))
            else:
                sanitized.append(item)
        
        if len(data) > 10:
            sanitized.append(f"...and {{len(data) - 10}} more items")
        
        return sanitized


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record with security sanitization."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add module and function info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add service info
        log_record['service'] = settings.service_name
        log_record['environment'] = settings.service_env
        
        # Add context variables if available
        if request_id := request_id_var.get():
            log_record['request_id'] = request_id
        
        if user_id := user_id_var.get():
            log_record['user_id'] = user_id
        
        if trace_id := trace_id_var.get():
            log_record['trace_id'] = trace_id
        
        # Add exception info if present (sanitized)
        is_production = settings.service_env in ["prod", "production"]
        if record.exc_info:
            exception_info = {
                'type': record.exc_info[0].__name__,
                'message': SecuritySanitizer.sanitize_string(str(record.exc_info[1])),
            }
            
            # Include traceback only in non-production
            if not is_production:
                exception_info['traceback'] = traceback.format_exception(*record.exc_info)
            
            log_record['exception'] = exception_info
        
        # Add extra fields with sanitization
        excluded_keys = ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                        'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                        'message', 'pathname', 'process', 'processName', 'relativeCreated',
                        'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']
        
        for key, value in record.__dict__.items():
            if key not in excluded_keys:
                # Sanitize based on production environment
                if is_production:
                    if isinstance(value, dict):
                        log_record[key] = SecuritySanitizer.sanitize_dict(value)
                    elif isinstance(value, list):
                        log_record[key] = SecuritySanitizer.sanitize_list(value)
                    elif isinstance(value, str):
                        log_record[key] = SecuritySanitizer.sanitize_string(value)
                    else:
                        log_record[key] = value
                else:
                    log_record[key] = value


class StructuredLogger:
    """Structured logger with context management."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_structured_logging()
    
    def _setup_structured_logging(self):
        """Setup structured JSON logging."""
        # Remove existing handlers
        self.logger.handlers = []
        
        # Create console handler with structured formatter
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Set level from environment or default
        import os
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        self.logger.setLevel(getattr(logging, log_level.upper()))
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Add context to logger."""
        for key, value in kwargs.items():
            if key == 'request_id':
                request_id_var.set(value)
            elif key == 'user_id':
                user_id_var.set(value)
            elif key == 'trace_id':
                trace_id_var.set(value)
        return self
    
    def info(self, message: str, **kwargs):
        """Log info message with extra fields and sanitization."""
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with extra fields and sanitization."""
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra fields and sanitization."""
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra fields and sanitization."""
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        self.logger.debug(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback and sanitization."""
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        self.logger.exception(message, extra=kwargs)
    
    def security_event(self, event_type: str, message: str, severity: str = "warning", **kwargs):
        """Log security-related events with special handling."""
        kwargs.update({
            'security_event': True,
            'event_type': event_type,
            'severity': severity,
        })
        
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        
        # Security events always logged as warnings or errors
        if severity.lower() in ["critical", "high"]:
            self.logger.error(f"🚨 SECURITY: {message}", extra=kwargs)
        else:
            self.logger.warning(f"⚠️ SECURITY: {message}", extra=kwargs)
    
    def audit_event(self, action: str, resource: str, result: str, **kwargs):
        """Log audit events for compliance and monitoring."""
        kwargs.update({
            'audit_event': True,
            'action': action,
            'resource': resource,
            'result': result,
        })
        
        message = f"AUDIT: {action} on {resource} -> {result}"
        is_production = settings.service_env in ["prod", "production"]
        if is_production:
            message = SecuritySanitizer.sanitize_string(message)
            kwargs = SecuritySanitizer.sanitize_dict(kwargs)
        
        self.logger.info(message, extra=kwargs)


class LoggerFactory:
    """Factory for creating structured loggers."""
    
    _loggers: Dict[str, StructuredLogger] = {}
    
    @classmethod
    def get_logger(cls, name: str) -> StructuredLogger:
        """Get or create a structured logger."""
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(name)
        return cls._loggers[name]


# Utility functions for common logging patterns
def log_api_request(logger: StructuredLogger, method: str, path: str, **kwargs):
    """Log API request with standard fields."""
    logger.info(
        f"API Request: {method} {path}",
        http_method=method,
        http_path=path,
        event_type="api_request",
        **kwargs
    )


def log_api_response(logger: StructuredLogger, status_code: int, duration_ms: float, **kwargs):
    """Log API response with standard fields."""
    logger.info(
        f"API Response: {status_code}",
        http_status=status_code,
        response_time_ms=duration_ms,
        event_type="api_response",
        **kwargs
    )


def log_external_call(logger: StructuredLogger, service: str, operation: str, **kwargs):
    """Log external service call."""
    logger.info(
        f"External call to {service}: {operation}",
        external_service=service,
        operation=operation,
        event_type="external_call",
        **kwargs
    )


def log_business_event(logger: StructuredLogger, event: str, **kwargs):
    """Log business domain event."""
    logger.info(
        f"Business event: {event}",
        business_event=event,
        event_type="business",
        **kwargs
    )


def log_performance_metric(logger: StructuredLogger, metric: str, value: float, unit: str = "ms", **kwargs):
    """Log performance metric."""
    logger.info(
        f"Performance: {metric} = {value}{unit}",
        metric_name=metric,
        metric_value=value,
        metric_unit=unit,
        event_type="performance",
        **kwargs
    )


# Decorators for automatic logging
def log_function_call(logger: Optional[StructuredLogger] = None):
    """Decorator to log function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = LoggerFactory.get_logger(func.__module__)
            
            logger.debug(
                f"Calling {func.__name__}",
                function=func.__name__,
                args=str(args)[:100],  # Truncate for safety
                kwargs=str(kwargs)[:100]
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"Completed {func.__name__}",
                    function=func.__name__,
                    success=True
                )
                return result
            except Exception as e:
                logger.exception(
                    f"Error in {func.__name__}",
                    function=func.__name__,
                    error_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator


# Configuration for different environments
class LogConfig:
    """Logging configuration for different environments."""
    
    @staticmethod
    def configure_for_environment(env: str):
        """Configure logging based on environment."""
        configs = {
            'development': {
                'level': 'DEBUG',
                'format': 'pretty',
                'include_trace': True
            },
            'staging': {
                'level': 'INFO',
                'format': 'json',
                'include_trace': True
            },
            'production': {
                'level': 'WARNING',
                'format': 'json',
                'include_trace': False
            }
        }
        
        config = configs.get(env, configs['development'])
        
        # Apply configuration
        logging.getLogger().setLevel(config['level'])
        
        # Additional environment-specific setup
        if env == 'production':
            # Disable debug logging for security
            logging.getLogger('asyncio').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)


# Example usage and patterns
if __name__ == "__main__":
    # Create logger
    logger = LoggerFactory.get_logger(__name__)
    
    # Basic logging
    logger.info("Application started", version="1.0.0", environment="development")
    
    # With context
    logger.with_context(request_id="req-123", user_id="user-456")
    logger.info("Processing user request", action="render", prompt_length=100)
    
    # Log API interaction
    log_api_request(logger, "POST", "/api/render", body_size=1024)
    log_api_response(logger, 200, 150.5, response_size=2048)
    
    # Log external service
    log_external_call(logger, "OpenRouter", "completion", model="gpt-4", tokens=500)
    
    # Log business event
    log_business_event(logger, "asset_generated", asset_id="asset-789", cost_usd=0.01)
    
    # Log performance
    log_performance_metric(logger, "image_processing", 250.3, "ms")
    
    # Example with decorator
    @log_function_call()
    def process_request(data: dict):
        return {"status": "processed"}
    
    result = process_request({"test": "data"})