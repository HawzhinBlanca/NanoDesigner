"""Retry mechanism with exponential backoff and jitter.

This module provides robust retry functionality for handling transient failures
in distributed systems.
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, List, Type, Union
from dataclasses import dataclass
from functools import wraps
import httpx

from ..core.structured_logging import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple = (0.0, 1.0)  # Multiplier range for jitter
    retryable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
    )
    retryable_status_codes: List[int] = [429, 500, 502, 503, 504]
    on_retry: Optional[Callable] = None  # Callback on each retry


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


class RetryManager:
    """Manager for retry logic with exponential backoff."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        # Exponential backoff
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_min, jitter_max = self.config.jitter_range
            jitter_multiplier = random.uniform(jitter_min, jitter_max)
            delay = delay * jitter_multiplier
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if the operation should be retried."""
        if attempt >= self.config.max_attempts:
            return False
        
        # Check if exception is retryable
        if isinstance(exception, self.config.retryable_exceptions):
            return True
        
        # Check for HTTP status codes
        if hasattr(exception, 'response'):
            response = exception.response
            if hasattr(response, 'status_code'):
                if response.status_code in self.config.retryable_status_codes:
                    return True
        
        return False
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Execute function with retry logic."""
        operation_name = operation_name or func.__name__
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                # Log attempt
                if attempt > 0:
                    logger.info(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} for {operation_name}"
                    )
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - return result
                if attempt > 0:
                    logger.info(f"Operation {operation_name} succeeded after {attempt + 1} attempts")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.should_retry(e, attempt + 1):
                    logger.error(
                        f"Operation {operation_name} failed with non-retryable error: {e}"
                    )
                    raise
                
                # Check if we've exhausted retries
                if attempt + 1 >= self.config.max_attempts:
                    logger.error(
                        f"Operation {operation_name} failed after {self.config.max_attempts} attempts"
                    )
                    raise RetryExhausted(
                        f"Operation {operation_name} failed after {self.config.max_attempts} attempts",
                        last_exception
                    )
                
                # Calculate delay
                delay = self.calculate_delay(attempt)
                
                logger.warning(
                    f"Operation {operation_name} failed (attempt {attempt + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                
                # Call retry callback if provided
                if self.config.on_retry:
                    self.config.on_retry(attempt + 1, delay, e)
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # Should not reach here, but just in case
        raise RetryExhausted(
            f"Operation {operation_name} failed after {self.config.max_attempts} attempts",
            last_exception
        )


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[tuple] = None,
    operation_name: Optional[str] = None
):
    """Decorator to add retry logic to functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions or RetryConfig().retryable_exceptions
            )
            manager = RetryManager(config)
            return await manager.execute_with_retry(
                func,
                *args,
                operation_name=operation_name or func.__name__,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions or RetryConfig().retryable_exceptions
            )
            manager = RetryManager(config)
            
            # Convert to async and run
            async def run():
                return await manager.execute_with_retry(
                    func,
                    *args,
                    operation_name=operation_name or func.__name__,
                    **kwargs
                )
            
            return asyncio.run(run())
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


class SmartRetry:
    """Advanced retry mechanism with adaptive behavior."""
    
    def __init__(self):
        self.failure_history: Dict[str, List[float]] = {}
        self.success_history: Dict[str, List[float]] = {}
    
    def get_adaptive_config(self, operation: str) -> RetryConfig:
        """Get adaptive retry configuration based on history."""
        config = RetryConfig()
        
        # Analyze failure patterns
        if operation in self.failure_history:
            failures = self.failure_history[operation]
            recent_failures = failures[-10:]  # Last 10 failures
            
            if len(recent_failures) > 5:
                # High failure rate - be more aggressive
                config.max_attempts = 5
                config.initial_delay = 2.0
                config.exponential_base = 1.5  # Less aggressive backoff
            
        # Analyze success patterns
        if operation in self.success_history:
            successes = self.success_history[operation]
            if len(successes) > 10:
                avg_success_time = sum(successes[-10:]) / 10
                if avg_success_time < 1.0:
                    # Fast operations - can retry quickly
                    config.initial_delay = 0.5
                    config.max_attempts = 4
        
        return config
    
    def record_failure(self, operation: str, duration: float):
        """Record a failure for adaptive behavior."""
        if operation not in self.failure_history:
            self.failure_history[operation] = []
        self.failure_history[operation].append(duration)
        
        # Keep only recent history
        if len(self.failure_history[operation]) > 100:
            self.failure_history[operation] = self.failure_history[operation][-100:]
    
    def record_success(self, operation: str, duration: float):
        """Record a success for adaptive behavior."""
        if operation not in self.success_history:
            self.success_history[operation] = []
        self.success_history[operation].append(duration)
        
        # Keep only recent history
        if len(self.success_history[operation]) > 100:
            self.success_history[operation] = self.success_history[operation][-100:]


# Global smart retry instance
smart_retry = SmartRetry()


async def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    *args,
    **kwargs
) -> Any:
    """Execute primary function with retry, fall back to alternative on failure."""
    try:
        # Try primary function with retry
        retry_manager = RetryManager(RetryConfig(max_attempts=2))
        return await retry_manager.execute_with_retry(
            primary_func,
            *args,
            operation_name=f"{primary_func.__name__}_primary",
            **kwargs
        )
    except (RetryExhausted, Exception) as e:
        logger.warning(f"Primary function failed, using fallback: {e}")
        
        # Try fallback function with retry
        retry_manager = RetryManager(RetryConfig(max_attempts=3))
        return await retry_manager.execute_with_retry(
            fallback_func,
            *args,
            operation_name=f"{fallback_func.__name__}_fallback",
            **kwargs
        )


# Pre-configured retry strategies
class RetryStrategies:
    """Common retry strategies for different scenarios."""
    
    @staticmethod
    def aggressive() -> RetryConfig:
        """Aggressive retry for critical operations."""
        return RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True
        )
    
    @staticmethod
    def conservative() -> RetryConfig:
        """Conservative retry for non-critical operations."""
        return RetryConfig(
            max_attempts=2,
            initial_delay=2.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True
        )
    
    @staticmethod
    def rate_limited() -> RetryConfig:
        """Retry strategy for rate-limited APIs."""
        return RetryConfig(
            max_attempts=4,
            initial_delay=5.0,
            max_delay=120.0,
            exponential_base=2.0,
            jitter=True,
            retryable_status_codes=[429]  # Only retry rate limit errors
        )
    
    @staticmethod
    def database() -> RetryConfig:
        """Retry strategy for database operations."""
        return RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
            )
        )