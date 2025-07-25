#!/usr/bin/env python3
"""
Error sanitization utilities for secure API responses.
Prevents internal error details from leaking to external users.
"""

import logging
import os

logger = logging.getLogger(__name__)


def sanitize_error_for_api(
    error: Exception, default_message: str = "Internal server error"
) -> str:
    """
    Sanitize error messages for API responses to prevent information leakage.

    Args:
        error: The exception that occurred
        default_message: Generic message to return to users

    Returns:
        Sanitized error message safe for external consumption
    """
    # SECURITY: Log error details only in development environment
    # Full stack traces could expose sensitive information in production logs
    environment = os.getenv("ENVIRONMENT", "production").lower()
    
    if environment in ["development", "dev", "testing", "test"]:
        # In development: Log full details for debugging
        logger.error(f"Internal error: {str(error)}", exc_info=True)
    else:
        # In production: Log minimal details to prevent information exposure
        error_type = type(error).__name__
        logger.error(f"Internal error ({error_type}): [REDACTED FOR SECURITY]")

    # Always return generic message to external users
    return default_message


def create_error_response(
    success: bool = False, message: str = "Operation failed", **kwargs
) -> dict:
    """
    Create a standardized error response for API endpoints.

    Args:
        success: Always False for error responses
        message: User-friendly error message
        **kwargs: Additional response fields

    Returns:
        Standardized error response dictionary
    """
    response = {"success": success, "error": message, **kwargs}
    return response
