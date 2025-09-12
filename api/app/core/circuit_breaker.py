"""Circuit breaker pattern implementation for fault tolerance.

This module provides circuit breaker functionality to prevent cascading failures
when external services are unavailable or experiencing issues.
"""

import asyncio
import time
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import functools
from collections import deque

from ..core.structured_logging import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds before trying half-open
    failure_rate_threshold: float = 0.5  # Failure rate to open circuit
    min_calls: int = 10  # Minimum calls before evaluating failure rate
    sliding_window_size: int = 100  # Size of sliding window for metrics
    excluded_exceptions: tuple = ()  # Exceptions that don't trigger the breaker


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: List[tuple] = field(default_factory=list)
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)


class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_open_time: Optional[float] = None
        self._sliding_window: deque = deque(maxlen=self.config.sliding_window_size)
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if circuit should be opened
            if self.state == CircuitState.CLOSED:
                if self._should_open_circuit():
                    await self._transition_to_open()
            
            # Check if circuit should transition to half-open
            elif self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    await self._transition_to_half_open()
            
            # Reject if circuit is open
            if self.state == CircuitState.OPEN:
                self.metrics.rejected_calls += 1
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        
        # Execute the function
        start_time = time.time()
        try:
            result = await self._execute_function(func, *args, **kwargs)
            response_time = time.time() - start_time
            
            async with self._lock:
                await self._on_success(response_time)
            
            return result
        
        except Exception as e:
            response_time = time.time() - start_time
            
            # Check if exception should trigger circuit breaker
            if not isinstance(e, self.config.excluded_exceptions):
                async with self._lock:
                    await self._on_failure(response_time, e)
            
            raise
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the wrapped function."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)
    
    async def _on_success(self, response_time: float):
        """Handle successful call."""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = datetime.now()
        self.metrics.response_times.append(response_time)
        self._sliding_window.append(True)
        
        self._consecutive_failures = 0
        self._consecutive_successes += 1
        
        # Transition from half-open to closed if threshold met
        if self.state == CircuitState.HALF_OPEN:
            if self._consecutive_successes >= self.config.success_threshold:
                await self._transition_to_closed()
        
        logger.debug(
            f"Circuit breaker '{self.name}' success",
            state=self.state.value,
            response_time_ms=response_time * 1000
        )
    
    async def _on_failure(self, response_time: float, error: Exception):
        """Handle failed call."""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = datetime.now()
        self.metrics.response_times.append(response_time)
        self._sliding_window.append(False)
        
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        
        logger.warning(
            f"Circuit breaker '{self.name}' failure",
            state=self.state.value,
            error=str(error),
            consecutive_failures=self._consecutive_failures
        )
        
        # Transition to open if in half-open state
        if self.state == CircuitState.HALF_OPEN:
            await self._transition_to_open()
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened."""
        # Check consecutive failures
        if self._consecutive_failures >= self.config.failure_threshold:
            return True
        
        # Check failure rate in sliding window
        if len(self._sliding_window) >= self.config.min_calls:
            failure_count = sum(1 for success in self._sliding_window if not success)
            failure_rate = failure_count / len(self._sliding_window)
            if failure_rate >= self.config.failure_rate_threshold:
                return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset to half-open."""
        if self._last_open_time is None:
            return False
        
        time_since_open = time.time() - self._last_open_time
        return time_since_open >= self.config.timeout
    
    async def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self._last_open_time = time.time()
        self.metrics.state_changes.append((datetime.now(), CircuitState.OPEN))
        
        logger.error(
            f"Circuit breaker '{self.name}' opened",
            consecutive_failures=self._consecutive_failures,
            failure_rate=self.metrics.failure_rate()
        )
    
    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self.metrics.state_changes.append((datetime.now(), CircuitState.HALF_OPEN))
        
        logger.info(f"Circuit breaker '{self.name}' half-opened for testing")
    
    async def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_open_time = None
        self.metrics.state_changes.append((datetime.now(), CircuitState.CLOSED))
        
        logger.info(f"Circuit breaker '{self.name}' closed (recovered)")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "rejected_calls": self.metrics.rejected_calls,
                "failure_rate": self.metrics.failure_rate(),
                "avg_response_time_ms": self.metrics.avg_response_time() * 1000,
                "consecutive_failures": self._consecutive_failures,
                "consecutive_successes": self._consecutive_successes
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout,
                "failure_rate_threshold": self.config.failure_rate_threshold
            }
        }
    
    async def reset(self):
        """Manually reset the circuit breaker."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._last_open_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global registry
circuit_breaker_registry = CircuitBreakerRegistry()


def with_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator to add circuit breaker to async functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = circuit_breaker_registry.get_or_create(name, config)
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# Pre-configured circuit breakers for common services
def get_openrouter_breaker() -> CircuitBreaker:
    """Get circuit breaker for OpenRouter API."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=30.0,
        failure_rate_threshold=0.5,
        min_calls=5
    )
    return circuit_breaker_registry.get_or_create("openrouter", config)


def get_s3_breaker() -> CircuitBreaker:
    """Get circuit breaker for S3 storage."""
    config = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=60.0,
        failure_rate_threshold=0.6,
        min_calls=10
    )
    return circuit_breaker_registry.get_or_create("s3_storage", config)


def get_database_breaker() -> CircuitBreaker:
    """Get circuit breaker for database."""
    config = CircuitBreakerConfig(
        failure_threshold=10,
        success_threshold=5,
        timeout=120.0,
        failure_rate_threshold=0.7,
        min_calls=20
    )
    return circuit_breaker_registry.get_or_create("database", config)