"""Retry manager with exponential backoff and circuit breaker."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategies."""
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"            # Linear backoff
    FIBONACCI = "fibonacci"      # Fibonacci backoff
    FIXED = "fixed"             # Fixed delay


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0     # seconds
    exponential_base: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True         # Add randomness to delays
    jitter_range: float = 0.1   # ±10% jitter
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5   # Failures before opening circuit
    success_threshold: int = 2   # Successes to close circuit
    timeout: float = 30.0        # Circuit open timeout
    half_open_max_calls: int = 3  # Max calls in half-open state
    
    # Retry conditions
    retry_on: List[type] = field(default_factory=lambda: [Exception])
    retry_on_result: Optional[Callable[[Any], bool]] = None
    

@dataclass
class RetryStatistics:
    """Statistics for retry operations."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    retried_calls: int = 0
    total_retries: int = 0
    circuit_opens: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls * 100
        
    @property
    def average_retries(self) -> float:
        """Calculate average retries per call."""
        if self.retried_calls == 0:
            return 0.0
        return self.total_retries / self.retried_calls


class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(self, config: RetryConfig):
        """Initialize circuit breaker.
        
        Args:
            config: Retry configuration
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        
    def call_succeeded(self):
        """Record successful call."""
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
            
    def call_failed(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
            
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._half_open_circuit()
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
            
        return False
        
    def _open_circuit(self):
        """Open the circuit."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        logger.warning("Circuit breaker opened due to failures")
        
    def _close_circuit(self):
        """Close the circuit."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info("Circuit breaker closed")
        
    def _half_open_circuit(self):
        """Set circuit to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        self.half_open_calls = 0
        logger.info("Circuit breaker half-opened for testing")
        
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.timeout


class RetryManager:
    """Manages retry operations with various strategies."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry manager.
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(self.config) if self.config.circuit_breaker_enabled else None
        self.statistics = RetryStatistics()
        
        # Fibonacci sequence for Fibonacci backoff
        self._fibonacci = [1, 1]
        
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
            
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * (attempt + 1)
            
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            while len(self._fibonacci) <= attempt:
                self._fibonacci.append(
                    self._fibonacci[-1] + self._fibonacci[-2]
                )
            delay = self.config.initial_delay * self._fibonacci[attempt]
            
        else:  # FIXED
            delay = self.config.initial_delay
            
        # Apply max delay cap
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            import random
            jitter = delay * self.config.jitter_range
            delay += random.uniform(-jitter, jitter)
            
        return max(0, delay)  # Ensure non-negative
        
    def should_retry(self, exception: Optional[Exception], result: Any) -> bool:
        """Check if operation should be retried.
        
        Args:
            exception: Exception raised (if any)
            result: Result returned (if no exception)
            
        Returns:
            True if should retry
        """
        if exception:
            # Check if exception type should be retried
            for exc_type in self.config.retry_on:
                if isinstance(exception, exc_type):
                    return True
            return False
            
        # Check result condition
        if self.config.retry_on_result:
            return self.config.retry_on_result(result)
            
        return False
        
    async def execute_async(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries failed
        """
        self.statistics.total_calls += 1
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            self.statistics.failed_calls += 1
            raise Exception("Circuit breaker is open")
            
        last_exception = None
        attempts = 0
        
        for attempt in range(self.config.max_attempts):
            attempts = attempt + 1
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Check if result should trigger retry
                if self.should_retry(None, result):
                    if attempt < self.config.max_attempts - 1:
                        delay = self.calculate_delay(attempt)
                        logger.debug(f"Retrying due to result condition (attempt {attempts}/{self.config.max_attempts}) after {delay:.2f}s")
                        await asyncio.sleep(delay)
                        self.statistics.total_retries += 1
                        continue
                        
                # Success
                if self.circuit_breaker:
                    self.circuit_breaker.call_succeeded()
                    
                self.statistics.successful_calls += 1
                self.statistics.last_success = datetime.utcnow()
                
                if attempt > 0:
                    self.statistics.retried_calls += 1
                    
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if should retry
                if not self.should_retry(e, None):
                    if self.circuit_breaker:
                        self.circuit_breaker.call_failed()
                    self.statistics.failed_calls += 1
                    self.statistics.last_failure = datetime.utcnow()
                    raise
                    
                # Check if more attempts available
                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempts}/{self.config.max_attempts} "
                        f"failed: {e}. Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    self.statistics.total_retries += 1
                else:
                    # All retries exhausted
                    if self.circuit_breaker:
                        self.circuit_breaker.call_failed()
                    self.statistics.failed_calls += 1
                    self.statistics.last_failure = datetime.utcnow()
                    logger.error(f"All retry attempts failed: {e}")
                    raise
                    
        # Should not reach here
        if last_exception:
            raise last_exception
        raise Exception("Unexpected retry state")
        
    def execute_sync(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute sync function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        # Convert to async and run
        async def async_wrapper():
            return func(*args, **kwargs)
            
        return asyncio.run(self.execute_async(async_wrapper))
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get retry statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_calls": self.statistics.total_calls,
            "successful_calls": self.statistics.successful_calls,
            "failed_calls": self.statistics.failed_calls,
            "retried_calls": self.statistics.retried_calls,
            "total_retries": self.statistics.total_retries,
            "success_rate": f"{self.statistics.success_rate:.1f}%",
            "average_retries": self.statistics.average_retries,
            "circuit_state": self.circuit_breaker.state.value if self.circuit_breaker else "disabled",
            "last_failure": self.statistics.last_failure.isoformat() if self.statistics.last_failure else None,
            "last_success": self.statistics.last_success.isoformat() if self.statistics.last_success else None,
        }
        
    def reset_statistics(self):
        """Reset statistics."""
        self.statistics = RetryStatistics()
        
    def reset_circuit_breaker(self):
        """Reset circuit breaker."""
        if self.circuit_breaker:
            self.circuit_breaker._close_circuit()


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    **kwargs
):
    """Decorator for adding retry logic to functions.
    
    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        strategy: Retry strategy
        **kwargs: Additional RetryConfig parameters
        
    Returns:
        Decorated function
    """
    def decorator(func):
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            strategy=strategy,
            **kwargs
        )
        retry_manager = RetryManager(config)
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_manager.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_manager.execute_sync(func, *args, **kwargs)
            return sync_wrapper
            
    return decorator