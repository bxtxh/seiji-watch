"""
Error Recovery System - Comprehensive error handling and recovery mechanisms.
Implements exponential backoff, circuit breakers, dead letter queues, and automatic recovery.
"""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF

    # Conditions for retry
    retry_on_exceptions: list[type] = field(default_factory=lambda: [Exception])
    retry_on_status_codes: list[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504])

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt."""
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (self.backoff_multiplier ** attempt)
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay
        else:  # IMMEDIATE
            delay = 0

        delay = min(delay, self.max_delay)

        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)  # Add jitter ±25%

        return delay


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures to open circuit
    success_threshold: int = 3  # Number of successes to close circuit
    timeout: float = 60.0  # Seconds to wait before trying half-open

    # Success/failure criteria
    success_status_codes: list[int] = field(
        default_factory=lambda: [200, 201, 202, 204])
    failure_exceptions: list[type] = field(default_factory=lambda: [Exception])


@dataclass
class OperationResult:
    """Result of an operation with error handling."""
    success: bool
    result: Any = None
    error: Exception | None = None
    attempts: int = 0
    total_duration: float = 0.0
    circuit_breaker_triggered: bool = False
    sent_to_dlq: bool = False
    recovery_applied: bool = False


@dataclass
class DeadLetterMessage:
    """Message in the dead letter queue."""
    id: str
    operation_name: str
    payload: dict[str, Any]
    original_error: str
    failed_at: datetime
    retry_count: int
    max_retries: int = 3
    next_retry_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'id': self.id,
            'operation_name': self.operation_name,
            'payload': self.payload,
            'original_error': self.original_error,
            'failed_at': self.failed_at.isoformat(),
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None}


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.last_state_change: datetime = datetime.now()

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        now = datetime.now()

        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and (
                    now - self.last_failure_time).total_seconds() >= self.config.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record a successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.last_state_change = datetime.now()
                logger.info(f"Circuit breaker {self.name} moved to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0  # Reset failure count on success

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.last_state_change = datetime.now()
                logger.warning(
                    f"Circuit breaker {self.name} moved to OPEN after {self.failure_count} failures")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.last_state_change = datetime.now()
            logger.warning(f"Circuit breaker {self.name} moved back to OPEN")

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_state_change': self.last_state_change.isoformat(),
            'can_execute': self.can_execute()}


class DeadLetterQueue:
    """Dead letter queue for failed operations."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.messages: dict[str, DeadLetterMessage] = {}
        self.retry_queue: list[str] = []  # Message IDs ready for retry

    def add_message(self, message: DeadLetterMessage):
        """Add a failed message to the DLQ."""
        if len(self.messages) >= self.max_size:
            # Remove oldest message
            oldest_id = min(
                self.messages.keys(),
                key=lambda k: self.messages[k].failed_at)
            del self.messages[oldest_id]
            if oldest_id in self.retry_queue:
                self.retry_queue.remove(oldest_id)

        self.messages[message.id] = message
        logger.info(f"Added message {message.id} to DLQ: {message.operation_name}")

    def get_retry_ready_messages(self) -> list[DeadLetterMessage]:
        """Get messages ready for retry."""
        now = datetime.now()
        ready_messages = []

        for message_id, message in self.messages.items():
            if (message.retry_count < message.max_retries and
                message.next_retry_at and
                    message.next_retry_at <= now):
                ready_messages.append(message)

        return ready_messages

    def remove_message(self, message_id: str):
        """Remove a message from the DLQ."""
        if message_id in self.messages:
            del self.messages[message_id]
            if message_id in self.retry_queue:
                self.retry_queue.remove(message_id)

    def get_statistics(self) -> dict[str, Any]:
        """Get DLQ statistics."""
        datetime.now()
        retry_ready = len(self.get_retry_ready_messages())

        by_operation = {}
        for message in self.messages.values():
            op_name = message.operation_name
            if op_name not in by_operation:
                by_operation[op_name] = {'count': 0, 'oldest': None}
            by_operation[op_name]['count'] += 1
            if by_operation[op_name]['oldest'] is None or message.failed_at < by_operation[op_name]['oldest']:
                by_operation[op_name]['oldest'] = message.failed_at

        return {
            'total_messages': len(self.messages),
            'retry_ready_messages': retry_ready,
            'messages_by_operation': by_operation,
            'oldest_message': min([m.failed_at for m in self.messages.values()]) if self.messages else None
        }


class ErrorRecoverySystem:
    """Comprehensive error recovery system."""

    def __init__(self):
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.dead_letter_queue = DeadLetterQueue()
        self.retry_configs: dict[str, RetryConfig] = {}
        self.recovery_procedures: dict[str, Callable] = {}

        # Default configurations
        self._setup_default_configs()

        # Statistics
        self.operation_stats: dict[str, dict[str, int]] = {}

    def _setup_default_configs(self):
        """Setup default retry and circuit breaker configurations."""

        # Default retry configs for different operation types
        self.retry_configs.update({
            'airtable_api': RetryConfig(
                max_attempts=5,
                base_delay=2.0,
                max_delay=30.0,
                backoff_multiplier=2.0,
                retry_on_status_codes=[429, 500, 502, 503, 504]
            ),
            'llm_api': RetryConfig(
                max_attempts=3,
                base_delay=5.0,
                max_delay=60.0,
                backoff_multiplier=1.5,
                retry_on_status_codes=[429, 500, 502, 503, 504]
            ),
            'discord_webhook': RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                backoff_multiplier=2.0
            ),
            'database_operation': RetryConfig(
                max_attempts=5,
                base_delay=0.5,
                max_delay=5.0,
                backoff_multiplier=1.5
            )
        })

        # Default circuit breaker configs
        circuit_configs = {
            'airtable_api': CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout=60.0
            ),
            'llm_api': CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=120.0
            ),
            'discord_webhook': CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=30.0
            )
        }

        for name, config in circuit_configs.items():
            self.circuit_breakers[name] = CircuitBreaker(name, config)

    def register_recovery_procedure(self, operation_name: str, procedure: Callable):
        """Register an automatic recovery procedure for an operation."""
        self.recovery_procedures[operation_name] = procedure
        logger.info(f"Registered recovery procedure for {operation_name}")

    async def execute_with_recovery(self,
                                    operation: Callable,
                                    operation_name: str,
                                    *args,
                                    **kwargs) -> OperationResult:
        """Execute an operation with full error recovery."""

        start_time = time.time()
        retry_config = self.retry_configs.get(operation_name, RetryConfig())
        circuit_breaker = self.circuit_breakers.get(operation_name)

        result = OperationResult(success=False)

        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            result.circuit_breaker_triggered = True
            result.error = Exception(f"Circuit breaker {operation_name} is OPEN")
            return result

        # Retry loop
        for attempt in range(retry_config.max_attempts):
            result.attempts = attempt + 1

            try:
                # Execute operation
                operation_result = await operation(*args, **kwargs)

                # Record success
                result.success = True
                result.result = operation_result

                if circuit_breaker:
                    circuit_breaker.record_success()

                self._record_operation_stat(operation_name, 'success')
                break

            except Exception as e:
                result.error = e

                # Record failure
                if circuit_breaker:
                    circuit_breaker.record_failure()

                self._record_operation_stat(operation_name, 'failure')

                # Check if we should retry
                should_retry = self._should_retry(e, attempt, retry_config)

                if should_retry and attempt < retry_config.max_attempts - 1:
                    delay = retry_config.calculate_delay(attempt)
                    logger.warning(
                        f"Operation {operation_name} failed (attempt {attempt + 1}), "
                        f"retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    # Final failure - try recovery procedures
                    if operation_name in self.recovery_procedures:
                        try:
                            await self.recovery_procedures[operation_name](*args, **kwargs)
                            result.recovery_applied = True
                            logger.info(
                                f"Applied recovery procedure for {operation_name}")
                        except Exception as recovery_error:
                            logger.error(
                                f"Recovery procedure failed for {operation_name}: {recovery_error}")

                    # Send to dead letter queue if configured
                    if attempt == retry_config.max_attempts - 1:
                        await self._send_to_dlq(operation_name, args, kwargs, e)
                        result.sent_to_dlq = True

                    break

        result.total_duration = time.time() - start_time
        return result

    def _should_retry(
            self,
            error: Exception,
            attempt: int,
            config: RetryConfig) -> bool:
        """Determine if operation should be retried."""

        # Check if exception type is retryable
        if not any(isinstance(error, exc_type)
                   for exc_type in config.retry_on_exceptions):
            return False

        # Check if status code is retryable (for HTTP errors)
        if hasattr(error, 'status_code'):
            return error.status_code in config.retry_on_status_codes

        return True

    async def _send_to_dlq(
        self,
        operation_name: str,
        args: tuple,
        kwargs: dict,
        error: Exception
    ):
        """Send failed operation to dead letter queue."""

        import uuid

        message = DeadLetterMessage(
            id=str(uuid.uuid4()),
            operation_name=operation_name,
            payload={
                'args': str(args),  # Convert to string for JSON serialization
                'kwargs': {k: str(v) for k, v in kwargs.items()}
            },
            original_error=str(error),
            failed_at=datetime.now(),
            retry_count=0,
            next_retry_at=datetime.now() + timedelta(minutes=30)  # Retry in 30 minutes
        )

        self.dead_letter_queue.add_message(message)
        logger.error(f"Sent operation {operation_name} to DLQ: {error}")

    def _record_operation_stat(self, operation_name: str, outcome: str):
        """Record operation statistics."""
        if operation_name not in self.operation_stats:
            self.operation_stats[operation_name] = {'success': 0, 'failure': 0}

        self.operation_stats[operation_name][outcome] += 1

    async def process_dlq_retries(self):
        """Process messages in the dead letter queue for retry."""

        retry_messages = self.dead_letter_queue.get_retry_ready_messages()

        for message in retry_messages:
            try:
                logger.info(
                    f"Retrying DLQ message {message.id}: {message.operation_name}")

                # Attempt to rebuild and retry the operation
                # This is a simplified approach - in production, you'd need more sophisticated
                # operation reconstruction from the payload

                message.retry_count += 1

                if message.retry_count >= message.max_retries:
                    # Give up and remove from DLQ
                    self.dead_letter_queue.remove_message(message.id)
                    logger.error(
                        f"Giving up on DLQ message {message.id} after {message.retry_count} retries")
                else:
                    # Schedule next retry
                    message.next_retry_at = datetime.now() + timedelta(minutes=60 * message.retry_count)
                    logger.info(
                        f"Scheduled next retry for {message.id} at {message.next_retry_at}")

            except Exception as e:
                logger.error(f"Failed to process DLQ message {message.id}: {e}")

    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status."""

        # Circuit breaker statuses
        circuit_statuses = {}
        for name, breaker in self.circuit_breakers.items():
            circuit_statuses[name] = breaker.get_status()

        # Operation statistics
        operation_stats = {}
        for op_name, stats in self.operation_stats.items():
            total = stats['success'] + stats['failure']
            success_rate = stats['success'] / total if total > 0 else 0
            operation_stats[op_name] = {
                'total_operations': total,
                'success_count': stats['success'],
                'failure_count': stats['failure'],
                'success_rate': success_rate
            }

        return {
            'circuit_breakers': circuit_statuses,
            'dead_letter_queue': self.dead_letter_queue.get_statistics(),
            'operation_statistics': operation_stats,
            'registered_recovery_procedures': list(self.recovery_procedures.keys()),
            'total_registered_operations': len(self.retry_configs)
        }

    async def health_check(self) -> bool:
        """Health check for error recovery system."""
        try:
            # Check if any circuit breakers are open
            open_breakers = [
                name for name, breaker in self.circuit_breakers.items()
                if breaker.state == CircuitBreakerState.OPEN
            ]

            # Check DLQ size
            dlq_stats = self.dead_letter_queue.get_statistics()
            dlq_overloaded = dlq_stats['total_messages'] > 500

            return len(open_breakers) == 0 and not dlq_overloaded

        except Exception as e:
            logger.error(f"Error recovery system health check failed: {e}")
            return False


# Global error recovery system instance
error_recovery_system = ErrorRecoverySystem()


# Decorator for easy integration
def with_error_recovery(operation_name: str):
    """Decorator to add error recovery to async functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await error_recovery_system.execute_with_recovery(
                func, operation_name, *args, **kwargs
            )
        return wrapper
    return decorator
