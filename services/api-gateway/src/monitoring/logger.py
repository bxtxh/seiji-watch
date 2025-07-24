"""Structured logging utilities for Diet Issue Tracker API Gateway."""

import json
import logging
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any

from fastapi import Request

# Context variables for request tracking
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
user_id_context: ContextVar[str] = ContextVar('user_id', default='anonymous')


class StructuredLogger:
    """Structured logging utility with Cloud Logging compatibility."""

    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplication
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Create structured formatter
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def _create_log_entry(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> dict[str, Any]:
        """Create structured log entry."""
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'severity': level.upper(),
            'message': message,
            'request_id': request_id_context.get(''),
            'user_id': user_id_context.get('anonymous'),
            'service': 'api-gateway',
            'version': '1.0.0'
        }

        # Add custom fields
        if kwargs:
            entry.update(kwargs)

        return entry

    def info(self, message: str, **kwargs):
        """Log info level message."""
        entry = self._create_log_entry('INFO', message, **kwargs)
        self.logger.info(json.dumps(entry))

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        entry = self._create_log_entry('WARNING', message, **kwargs)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, error: Exception | None = None, **kwargs):
        """Log error level message."""
        entry = self._create_log_entry('ERROR', message, **kwargs)

        if error:
            entry.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'stack_trace': traceback.format_exc()
            })

        self.logger.error(json.dumps(entry))

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        entry = self._create_log_entry('DEBUG', message, **kwargs)
        self.logger.debug(json.dumps(entry))

    def api_request(
        self,
        request: Request,
        response_status: int,
        response_time_ms: float,
        **kwargs
    ):
        """Log API request with structured data."""
        entry = self._create_log_entry(
            'INFO',
            f"{request.method} {request.url.path}",
            http_method=request.method,
            http_url=str(request.url),
            http_status=response_status,
            http_response_time_ms=response_time_ms,
            http_user_agent=request.headers.get('user-agent', ''),
            http_remote_addr=request.client.host if request.client else '',
            **kwargs
        )
        self.logger.info(json.dumps(entry))

    def security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        **kwargs
    ):
        """Log security-related events."""
        entry = self._create_log_entry(
            severity.upper(),
            description,
            security_event_type=event_type,
            security_severity=severity,
            **kwargs
        )
        self.logger.log(getattr(logging, severity.upper()), json.dumps(entry))

    def performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'ms',
        **kwargs
    ):
        """Log performance metrics."""
        entry = self._create_log_entry(
            'INFO',
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs
        )
        self.logger.info(json.dumps(entry))

    def business_event(
        self,
        event_type: str,
        description: str,
        **kwargs
    ):
        """Log business logic events."""
        entry = self._create_log_entry(
            'INFO',
            description,
            business_event_type=event_type,
            **kwargs
        )
        self.logger.info(json.dumps(entry))


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record):
        # Return the message as-is since it's already JSON formatted
        return record.getMessage()


class RequestContextMiddleware:
    """Middleware to set request context for logging."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate request ID
            request_id = str(uuid.uuid4())
            request_id_context.set(request_id)

            # Set user ID if available (from headers or auth)
            headers = dict(scope["headers"])
            user_id = headers.get(b"x-user-id", b"anonymous").decode()
            user_id_context.set(user_id)

            # Add request ID to response headers
            async def send_with_request_id(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append([b"x-request-id", request_id.encode()])
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_request_id)
        else:
            await self.app(scope, receive, send)


# Global logger instance
structured_logger = StructuredLogger("api-gateway")

# Convenience functions


def log_info(message: str, **kwargs):
    """Log info message."""
    structured_logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message."""
    structured_logger.warning(message, **kwargs)


def log_error(message: str, error: Exception | None = None, **kwargs):
    """Log error message."""
    structured_logger.error(message, error=error, **kwargs)


def log_debug(message: str, **kwargs):
    """Log debug message."""
    structured_logger.debug(message, **kwargs)


def log_api_request(
        request: Request,
        response_status: int,
        response_time_ms: float,
        **kwargs):
    """Log API request."""
    structured_logger.api_request(request, response_status, response_time_ms, **kwargs)


def log_security_event(event_type: str, severity: str, description: str, **kwargs):
    """Log security event."""
    structured_logger.security_event(event_type, severity, description, **kwargs)


def log_performance_metric(metric_name: str, value: float, unit: str = 'ms', **kwargs):
    """Log performance metric."""
    structured_logger.performance_metric(metric_name, value, unit, **kwargs)


def log_business_event(event_type: str, description: str, **kwargs):
    """Log business event."""
    structured_logger.business_event(event_type, description, **kwargs)
