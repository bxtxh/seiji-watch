"""Error recovery and compensation mechanisms."""

from __future__ import annotations

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors for categorization."""
    CONNECTION = "connection"        # Network/connection errors
    TIMEOUT = "timeout"             # Operation timeouts
    RATE_LIMIT = "rate_limit"       # Rate limiting errors
    DATA_INTEGRITY = "data_integrity"  # Data consistency errors
    PERMISSION = "permission"        # Authorization errors
    VALIDATION = "validation"        # Data validation errors
    RESOURCE = "resource"           # Resource unavailable
    UNKNOWN = "unknown"             # Unclassified errors


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"                 # Simple retry
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Retry with exponential backoff
    FALLBACK = "fallback"           # Use fallback service/data
    COMPENSATE = "compensate"       # Compensating transaction
    SKIP = "skip"                   # Skip and continue
    QUEUE = "queue"                 # Queue for later processing
    ALERT = "alert"                 # Alert and wait for manual intervention
    CIRCUIT_BREAK = "circuit_break"  # Open circuit breaker


@dataclass
class ErrorContext:
    """Context information for an error."""
    error_type: ErrorType
    error_message: str
    traceback: str
    timestamp: datetime
    component: str
    operation: str
    data: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovered: bool = False
    

@dataclass
class RecoveryRule:
    """Rule for error recovery."""
    error_type: ErrorType
    strategy: RecoveryStrategy
    max_attempts: int = 3
    delay_seconds: float = 1.0
    fallback_handler: Optional[Callable] = None
    compensation_handler: Optional[Callable] = None
    condition: Optional[Callable[[ErrorContext], bool]] = None
    priority: int = 0  # Higher priority rules are evaluated first
    

class ErrorRecoveryService:
    """Service for managing error recovery and compensation."""
    
    def __init__(self):
        """Initialize error recovery service."""
        self.recovery_rules: List[RecoveryRule] = []
        self.error_history: List[ErrorContext] = []
        self.recovery_handlers: Dict[RecoveryStrategy, Callable] = {}
        self.compensation_log: List[Dict[str, Any]] = []
        self.failed_operations: Set[str] = set()
        self.recovery_queue: asyncio.Queue = asyncio.Queue()
        self.circuit_breakers: Dict[str, bool] = {}  # component -> is_open
        
        # Register default handlers
        self._register_default_handlers()
        self._register_default_rules()
        
    def _register_default_handlers(self):
        """Register default recovery handlers."""
        self.recovery_handlers[RecoveryStrategy.RETRY] = self._handle_retry
        self.recovery_handlers[RecoveryStrategy.EXPONENTIAL_BACKOFF] = self._handle_exponential_backoff
        self.recovery_handlers[RecoveryStrategy.FALLBACK] = self._handle_fallback
        self.recovery_handlers[RecoveryStrategy.COMPENSATE] = self._handle_compensate
        self.recovery_handlers[RecoveryStrategy.SKIP] = self._handle_skip
        self.recovery_handlers[RecoveryStrategy.QUEUE] = self._handle_queue
        self.recovery_handlers[RecoveryStrategy.ALERT] = self._handle_alert
        self.recovery_handlers[RecoveryStrategy.CIRCUIT_BREAK] = self._handle_circuit_break
        
    def _register_default_rules(self):
        """Register default recovery rules."""
        # Connection errors -> Exponential backoff
        self.add_recovery_rule(
            RecoveryRule(
                error_type=ErrorType.CONNECTION,
                strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=5,
                delay_seconds=2.0,
                priority=10
            )
        )
        
        # Rate limit errors -> Exponential backoff with longer delays
        self.add_recovery_rule(
            RecoveryRule(
                error_type=ErrorType.RATE_LIMIT,
                strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=3,
                delay_seconds=10.0,
                priority=10
            )
        )
        
        # Timeout errors -> Simple retry
        self.add_recovery_rule(
            RecoveryRule(
                error_type=ErrorType.TIMEOUT,
                strategy=RecoveryStrategy.RETRY,
                max_attempts=3,
                delay_seconds=1.0,
                priority=5
            )
        )
        
        # Data integrity errors -> Alert and compensate
        self.add_recovery_rule(
            RecoveryRule(
                error_type=ErrorType.DATA_INTEGRITY,
                strategy=RecoveryStrategy.COMPENSATE,
                max_attempts=1,
                priority=20
            )
        )
        
        # Permission errors -> Alert (no retry)
        self.add_recovery_rule(
            RecoveryRule(
                error_type=ErrorType.PERMISSION,
                strategy=RecoveryStrategy.ALERT,
                max_attempts=1,
                priority=15
            )
        )
        
    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an error into an ErrorType.
        
        Args:
            error: The exception to classify
            
        Returns:
            Classified error type
        """
        error_str = str(error).lower()
        error_type_str = type(error).__name__.lower()
        
        # Connection errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['connection', 'network', 'socket', 'refused', 'reset']):
            return ErrorType.CONNECTION
            
        # Timeout errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['timeout', 'timed out', 'deadline']):
            return ErrorType.TIMEOUT
            
        # Rate limit errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['rate limit', 'throttl', 'too many requests', '429']):
            return ErrorType.RATE_LIMIT
            
        # Permission errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['permission', 'unauthorized', 'forbidden', '401', '403']):
            return ErrorType.PERMISSION
            
        # Validation errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['validation', 'invalid', 'constraint', 'format']):
            return ErrorType.VALIDATION
            
        # Data integrity errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['integrity', 'consistency', 'conflict', 'duplicate']):
            return ErrorType.DATA_INTEGRITY
            
        # Resource errors
        if any(keyword in error_str or keyword in error_type_str for keyword in 
               ['not found', '404', 'missing', 'unavailable']):
            return ErrorType.RESOURCE
            
        return ErrorType.UNKNOWN
        
    def add_recovery_rule(self, rule: RecoveryRule):
        """Add a recovery rule.
        
        Args:
            rule: Recovery rule to add
        """
        self.recovery_rules.append(rule)
        self.recovery_rules.sort(key=lambda r: r.priority, reverse=True)
        
    async def handle_error(
        self,
        error: Exception,
        component: str,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        retry_func: Optional[Callable] = None
    ) -> Any:
        """Handle an error with recovery strategy.
        
        Args:
            error: The exception that occurred
            component: Component where error occurred
            operation: Operation that failed
            data: Additional context data
            retry_func: Function to retry if applicable
            
        Returns:
            Recovery result or raises exception
        """
        # Create error context
        error_type = self.classify_error(error)
        context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            traceback=traceback.format_exc(),
            timestamp=datetime.utcnow(),
            component=component,
            operation=operation,
            data=data or {}
        )
        
        # Log error
        self.error_history.append(context)
        logger.error(
            f"Error in {component}.{operation}: {error_type.value} - {error}"
        )
        
        # Find matching recovery rule
        rule = self._find_recovery_rule(context)
        if not rule:
            logger.error(f"No recovery rule found for {error_type.value}")
            raise error
            
        context.recovery_strategy = rule.strategy
        
        # Execute recovery strategy
        try:
            handler = self.recovery_handlers.get(rule.strategy)
            if handler:
                result = await handler(context, rule, retry_func)
                context.recovered = True
                return result
            else:
                logger.error(f"No handler for strategy {rule.strategy.value}")
                raise error
                
        except Exception as recovery_error:
            logger.error(f"Recovery failed: {recovery_error}")
            context.recovered = False
            raise
            
    def _find_recovery_rule(self, context: ErrorContext) -> Optional[RecoveryRule]:
        """Find matching recovery rule for error context.
        
        Args:
            context: Error context
            
        Returns:
            Matching recovery rule or None
        """
        for rule in self.recovery_rules:
            # Check error type match
            if rule.error_type != context.error_type:
                continue
                
            # Check custom condition
            if rule.condition and not rule.condition(context):
                continue
                
            return rule
            
        return None
        
    async def _handle_retry(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle simple retry strategy."""
        if not retry_func:
            raise Exception("No retry function provided")
            
        for attempt in range(rule.max_attempts):
            context.attempts = attempt + 1
            
            try:
                logger.info(
                    f"Retry attempt {context.attempts}/{rule.max_attempts} "
                    f"for {context.component}.{context.operation}"
                )
                
                if attempt > 0:
                    await asyncio.sleep(rule.delay_seconds)
                    
                return await retry_func()
                
            except Exception as e:
                if attempt == rule.max_attempts - 1:
                    raise
                logger.warning(f"Retry {attempt + 1} failed: {e}")
                
    async def _handle_exponential_backoff(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle exponential backoff strategy."""
        if not retry_func:
            raise Exception("No retry function provided")
            
        for attempt in range(rule.max_attempts):
            context.attempts = attempt + 1
            delay = rule.delay_seconds * (2 ** attempt)
            
            try:
                logger.info(
                    f"Exponential backoff attempt {context.attempts}/{rule.max_attempts} "
                    f"(delay: {delay}s) for {context.component}.{context.operation}"
                )
                
                if attempt > 0:
                    await asyncio.sleep(delay)
                    
                return await retry_func()
                
            except Exception as e:
                if attempt == rule.max_attempts - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
    async def _handle_fallback(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle fallback strategy."""
        if rule.fallback_handler:
            logger.info(f"Using fallback for {context.component}.{context.operation}")
            return await rule.fallback_handler(context)
        raise Exception("No fallback handler provided")
        
    async def _handle_compensate(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle compensation strategy."""
        if rule.compensation_handler:
            logger.info(f"Executing compensation for {context.component}.{context.operation}")
            
            # Log compensation
            self.compensation_log.append({
                "timestamp": datetime.utcnow(),
                "component": context.component,
                "operation": context.operation,
                "error": context.error_message,
                "data": context.data
            })
            
            return await rule.compensation_handler(context)
        raise Exception("No compensation handler provided")
        
    async def _handle_skip(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle skip strategy."""
        logger.warning(
            f"Skipping failed operation {context.component}.{context.operation}"
        )
        self.failed_operations.add(f"{context.component}.{context.operation}")
        return None
        
    async def _handle_queue(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle queue strategy."""
        logger.info(
            f"Queueing failed operation {context.component}.{context.operation} "
            f"for later processing"
        )
        
        await self.recovery_queue.put({
            "context": context,
            "retry_func": retry_func,
            "queued_at": datetime.utcnow()
        })
        
        return None
        
    async def _handle_alert(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle alert strategy."""
        logger.critical(
            f"ALERT: Manual intervention required for "
            f"{context.component}.{context.operation} - {context.error_message}"
        )
        
        # In production, this would send alerts via monitoring system
        # For now, just log and raise
        raise Exception(
            f"Manual intervention required: {context.error_message}"
        )
        
    async def _handle_circuit_break(
        self,
        context: ErrorContext,
        rule: RecoveryRule,
        retry_func: Optional[Callable]
    ) -> Any:
        """Handle circuit breaker strategy."""
        logger.warning(
            f"Opening circuit breaker for {context.component}"
        )
        
        self.circuit_breakers[context.component] = True
        
        # Schedule circuit breaker reset
        asyncio.create_task(
            self._reset_circuit_breaker(context.component, delay=30)
        )
        
        raise Exception(
            f"Circuit breaker open for {context.component}"
        )
        
    async def _reset_circuit_breaker(self, component: str, delay: float):
        """Reset circuit breaker after delay."""
        await asyncio.sleep(delay)
        self.circuit_breakers[component] = False
        logger.info(f"Circuit breaker reset for {component}")
        
    async def process_recovery_queue(self):
        """Process queued recovery operations."""
        while not self.recovery_queue.empty():
            item = await self.recovery_queue.get()
            
            context = item["context"]
            retry_func = item["retry_func"]
            queued_duration = (datetime.utcnow() - item["queued_at"]).total_seconds()
            
            # Skip if queued too long
            if queued_duration > 3600:  # 1 hour
                logger.warning(
                    f"Skipping queued operation {context.component}.{context.operation} "
                    f"(queued for {queued_duration}s)"
                )
                continue
                
            try:
                logger.info(
                    f"Processing queued operation {context.component}.{context.operation}"
                )
                if retry_func:
                    await retry_func()
                    
            except Exception as e:
                logger.error(
                    f"Queued operation failed: {context.component}.{context.operation} - {e}"
                )
                
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error and recovery statistics.
        
        Returns:
            Statistics dictionary
        """
        # Group errors by type
        errors_by_type = defaultdict(int)
        recoveries_by_strategy = defaultdict(int)
        recovery_success_rate = 0
        
        for error in self.error_history:
            errors_by_type[error.error_type.value] += 1
            if error.recovery_strategy:
                recoveries_by_strategy[error.recovery_strategy.value] += 1
                
        # Calculate recovery rate
        total_errors = len(self.error_history)
        recovered_errors = sum(1 for e in self.error_history if e.recovered)
        if total_errors > 0:
            recovery_success_rate = (recovered_errors / total_errors) * 100
            
        return {
            "total_errors": total_errors,
            "recovered_errors": recovered_errors,
            "recovery_success_rate": f"{recovery_success_rate:.1f}%",
            "errors_by_type": dict(errors_by_type),
            "recoveries_by_strategy": dict(recoveries_by_strategy),
            "failed_operations": list(self.failed_operations),
            "compensation_count": len(self.compensation_log),
            "queued_operations": self.recovery_queue.qsize(),
            "open_circuit_breakers": [
                comp for comp, is_open in self.circuit_breakers.items() if is_open
            ],
        }
        
    def clear_history(self):
        """Clear error history and statistics."""
        self.error_history.clear()
        self.compensation_log.clear()
        self.failed_operations.clear()