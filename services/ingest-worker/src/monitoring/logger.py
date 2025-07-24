"""
Structured Logging System for Ingest Worker

This module provides comprehensive logging capabilities with:
- Structured JSON logging for cloud environments
- Contextual logging with request/operation tracing
- Performance logging with timing information
- Error tracking with stack traces and context
- Security event logging
- Audit trail for data processing operations
"""

import json
import logging
import sys
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# Thread-local storage for context
_local = threading.local()


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log event categories."""
    SYSTEM = "system"
    PROCESSING = "processing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    ERROR = "error"
    USER_ACTION = "user_action"


@dataclass
class LogContext:
    """Contextual information for logging."""
    request_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    operation_id: str | None = None
    trace_id: str | None = None
    component: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class StructuredLogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    category: str
    service: str = "ingest_worker"
    version: str = "1.0.0"
    context: dict[str, str] = None
    data: dict[str, Any] = None
    performance: dict[str, float] = None
    error: dict[str, Any] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        # Remove None values
        entry_dict = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(entry_dict, default=str, ensure_ascii=False)


class StructuredLogger:
    """Structured logger with context support."""

    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup the underlying logger."""
        self.logger.setLevel(getattr(logging, self.level.value))

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add structured handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False

    def _get_context(self) -> LogContext:
        """Get current logging context."""
        return getattr(_local, 'context', LogContext())

    def _create_entry(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory,
        data: dict[str, Any] = None,
        performance: dict[str, float] = None,
        error: dict[str, Any] = None
    ) -> StructuredLogEntry:
        """Create a structured log entry."""
        context = self._get_context()

        return StructuredLogEntry(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            level=level.value,
            message=message,
            category=category.value,
            context=context.to_dict() if context else None,
            data=data,
            performance=performance,
            error=error
        )

    def debug(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log debug message."""
        entry = self._create_entry(LogLevel.DEBUG, message, category, **kwargs)
        self.logger.debug(entry.to_json())

    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log info message."""
        entry = self._create_entry(LogLevel.INFO, message, category, **kwargs)
        self.logger.info(entry.to_json())

    def warning(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log warning message."""
        entry = self._create_entry(LogLevel.WARNING, message, category, **kwargs)
        self.logger.warning(entry.to_json())

    def error(self, message: str, category: LogCategory = LogCategory.ERROR, **kwargs):
        """Log error message."""
        entry = self._create_entry(LogLevel.ERROR, message, category, **kwargs)
        self.logger.error(entry.to_json())

    def critical(self, message: str, category: LogCategory = LogCategory.ERROR, **kwargs):
        """Log critical message."""
        entry = self._create_entry(LogLevel.CRITICAL, message, category, **kwargs)
        self.logger.critical(entry.to_json())

    def log_exception(
        self,
        exception: Exception,
        message: str = None,
        category: LogCategory = LogCategory.ERROR,
        **kwargs
    ):
        """Log an exception with full context."""
        error_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'stack_trace': traceback.format_exc()
        }

        log_message = message or f"Exception occurred: {type(exception).__name__}"

        self.error(log_message, category, error=error_data, **kwargs)

    def log_performance(
        self,
        operation: str,
        duration: float,
        details: dict[str, Any] = None,
        success: bool = True
    ):
        """Log performance metrics."""
        performance_data = {
            'duration_seconds': duration,
            'operation': operation,
            'success': success
        }

        message = f"Operation {operation} completed in {duration:.3f}s"
        if not success:
            message += " (failed)"

        self.info(
            message,
            LogCategory.PERFORMANCE,
            data=details,
            performance=performance_data
        )

    def log_audit(
        self,
        action: str,
        resource: str,
        details: dict[str, Any] = None
    ):
        """Log audit event."""
        audit_data = {
            'action': action,
            'resource': resource,
            'timestamp': datetime.utcnow().isoformat()
        }

        if details:
            audit_data.update(details)

        self.info(
            f"Audit: {action} on {resource}",
            LogCategory.AUDIT,
            data=audit_data
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: dict[str, Any] = None
    ):
        """Log security event."""
        security_data = {
            'event_type': event_type,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat()
        }

        if details:
            security_data.update(details)

        log_level = LogLevel.WARNING if severity in ['medium', 'high'] else LogLevel.INFO

        entry = self._create_entry(
            log_level,
            f"Security event: {event_type}",
            LogCategory.SECURITY,
            data=security_data
        )

        getattr(self.logger, log_level.value.lower())(entry.to_json())

    def log_data_processing(
        self,
        operation: str,
        input_count: int,
        output_count: int,
        success: bool = True,
        duration: float | None = None,
        quality_score: float | None = None
    ):
        """Log data processing operation."""
        processing_data = {
            'operation': operation,
            'input_count': input_count,
            'output_count': output_count,
            'success': success,
            'efficiency_ratio': output_count / input_count if input_count > 0 else 0
        }

        if duration:
            processing_data['duration_seconds'] = duration
            processing_data['throughput_per_second'] = input_count / duration if duration > 0 else 0

        if quality_score:
            processing_data['quality_score'] = quality_score

        message = f"Data processing: {operation} processed {input_count} items, produced {output_count} results"
        if not success:
            message += " (failed)"

        self.info(
            message,
            LogCategory.PROCESSING,
            data=processing_data,
            performance={'duration_seconds': duration} if duration else None
        )


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logs."""

    def format(self, record):
        # The record.msg should already be a JSON string
        return record.getMessage()


@contextmanager
def logging_context(
    request_id: str = None,
    session_id: str = None,
    user_id: str = None,
    operation_id: str = None,
    trace_id: str = None,
    component: str = None
):
    """Context manager for setting logging context."""
    # Generate IDs if not provided
    if not request_id:
        request_id = str(uuid.uuid4())
    if not operation_id:
        operation_id = str(uuid.uuid4())
    if not trace_id:
        trace_id = str(uuid.uuid4())

    context = LogContext(
        request_id=request_id,
        session_id=session_id,
        user_id=user_id,
        operation_id=operation_id,
        trace_id=trace_id,
        component=component
    )

    # Store in thread-local storage
    old_context = getattr(_local, 'context', None)
    _local.context = context

    try:
        yield context
    finally:
        _local.context = old_context


@contextmanager
def timed_operation(logger: StructuredLogger, operation_name: str, **kwargs):
    """Context manager for timing operations with logging."""
    start_time = time.time()
    operation_id = str(uuid.uuid4())

    with logging_context(operation_id=operation_id, component=operation_name):
        logger.info(f"Starting operation: {operation_name}", LogCategory.PROCESSING, data=kwargs)

        success = True
        try:
            yield operation_id
        except Exception as e:
            success = False
            logger.log_exception(e, f"Operation failed: {operation_name}")
            raise
        finally:
            duration = time.time() - start_time
            logger.log_performance(operation_name, duration, kwargs, success)


# Global logger instances
system_logger = StructuredLogger("ingest_worker.system")
processing_logger = StructuredLogger("ingest_worker.processing")
security_logger = StructuredLogger("ingest_worker.security")
performance_logger = StructuredLogger("ingest_worker.performance")


# Convenience functions
def log_info(message: str, **kwargs):
    """Log info message to system logger."""
    system_logger.info(message, **kwargs)


def log_error(message: str, **kwargs):
    """Log error message to system logger."""
    system_logger.error(message, **kwargs)


def log_exception(exception: Exception, message: str = None, **kwargs):
    """Log exception to system logger."""
    system_logger.log_exception(exception, message, **kwargs)


def log_processing(operation: str, input_count: int, output_count: int, **kwargs):
    """Log data processing operation."""
    processing_logger.log_data_processing(operation, input_count, output_count, **kwargs)


def log_security(event_type: str, severity: str, **kwargs):
    """Log security event."""
    security_logger.log_security_event(event_type, severity, **kwargs)


def log_performance(operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    performance_logger.log_performance(operation, duration, **kwargs)


def log_audit(action: str, resource: str, **kwargs):
    """Log audit event."""
    system_logger.log_audit(action, resource, **kwargs)


# Setup root logger to use structured format
def setup_structured_logging(level: str = "INFO"):
    """Setup structured logging for the entire application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add structured handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)
