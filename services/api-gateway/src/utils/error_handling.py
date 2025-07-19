"""
Enhanced Error Handling Utilities
Provides specific error types and better error context for debugging.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorCode(Enum):
    """Specific error codes for better error handling."""
    
    # Authentication/Authorization
    INVALID_TOKEN = "INVALID_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Validation
    INVALID_INPUT = "INVALID_INPUT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    
    # External Services
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    AIRTABLE_ERROR = "AIRTABLE_ERROR"
    LLM_ERROR = "LLM_ERROR"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    
    # Internal
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class ServiceError(Exception):
    """Base exception for service-specific errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode, 
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

class ValidationError(ServiceError):
    """Validation-specific error."""
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_FAILED,
            details={"field": field, **(details or {})},
            status_code=422
        )

class AuthenticationError(ServiceError):
    """Authentication-specific error."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.INVALID_TOKEN):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401
        )

class AuthorizationError(ServiceError):
    """Authorization-specific error."""
    
    def __init__(self, message: str, required_permission: str = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            details={"required_permission": required_permission},
            status_code=403
        )

class ExternalServiceError(ServiceError):
    """External service communication error."""
    
    def __init__(self, service_name: str, message: str, error_code: ErrorCode, response_code: int = None):
        super().__init__(
            message=f"{service_name}: {message}",
            error_code=error_code,
            details={"service": service_name, "response_code": response_code},
            status_code=503
        )

class RateLimitError(ServiceError):
    """Rate limiting error."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details={"retry_after": retry_after},
            status_code=429
        )

def handle_service_error(error: ServiceError) -> HTTPException:
    """Convert ServiceError to HTTPException with proper logging."""
    
    # Log error with context
    logger.error(
        f"Service error: {error.error_code.value} - {error.message}",
        extra={
            "error_code": error.error_code.value,
            "details": error.details,
            "status_code": error.status_code
        }
    )
    
    # Create response
    return HTTPException(
        status_code=error.status_code,
        detail={
            "error": error.error_code.value,
            "message": error.message,
            "details": error.details
        }
    )

def handle_unexpected_error(error: Exception, operation: str) -> HTTPException:
    """Handle unexpected errors with proper logging."""
    
    error_id = f"err_{hash(str(error)) % 10000:04d}"
    
    logger.error(
        f"Unexpected error in {operation}: {type(error).__name__}: {str(error)}",
        extra={
            "error_id": error_id,
            "operation": operation,
            "error_type": type(error).__name__
        },
        exc_info=True
    )
    
    return HTTPException(
        status_code=500,
        detail={
            "error": ErrorCode.UNEXPECTED_ERROR.value,
            "message": f"An unexpected error occurred during {operation}",
            "error_id": error_id
        }
    )

# Context managers for error handling
class ErrorContext:
    """Context manager for handling errors in a specific operation."""
    
    def __init__(self, operation: str):
        self.operation = operation
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        
        if isinstance(exc_val, ServiceError):
            # Re-raise service errors as-is
            return False
        
        # Convert unexpected errors
        raise handle_unexpected_error(exc_val, self.operation)

# Decorator for error handling
def handle_errors(operation: str):
    """Decorator to handle errors in API endpoints."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ServiceError as e:
                raise handle_service_error(e)
            except Exception as e:
                raise handle_unexpected_error(e, operation)
        return wrapper
    return decorator

# Validation helpers
def validate_record_id(record_id: str, field_name: str = "record_id") -> str:
    """Validate Airtable record ID format."""
    import re
    
    if not isinstance(record_id, str):
        raise ValidationError(f"{field_name} must be a string", field_name)
    
    if not re.match(r'^rec[a-zA-Z0-9]{14}$', record_id):
        raise ValidationError(f"Invalid {field_name} format", field_name)
    
    return record_id

def validate_pagination(offset: int = 0, limit: int = 50, max_limit: int = 1000) -> tuple:
    """Validate pagination parameters."""
    if offset < 0:
        raise ValidationError("Offset must be non-negative", "offset")
    
    if limit < 1:
        raise ValidationError("Limit must be positive", "limit")
    
    if limit > max_limit:
        raise ValidationError(f"Limit cannot exceed {max_limit}", "limit")
    
    return offset, limit

def validate_enum_value(value: str, enum_class: Enum, field_name: str) -> str:
    """Validate that value is in enum."""
    try:
        enum_class(value)
        return value
    except ValueError:
        valid_values = [e.value for e in enum_class]
        raise ValidationError(
            f"{field_name} must be one of: {', '.join(valid_values)}", 
            field_name,
            {"valid_values": valid_values}
        )