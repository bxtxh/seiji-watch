"""
Standardized API response format utilities.
Ensures consistent response structure across all endpoints.
"""

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class APIResponse:
    """Standardized API response formatter."""

    @staticmethod
    def success(
        data: Any,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
        count: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a successful response.

        Args:
            data: The response data
            message: Optional success message
            metadata: Optional metadata (pagination, timestamps, etc.)
            count: Optional count of items (for list responses)

        Returns:
            Standardized success response dict
        """
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }

        if message:
            response["message"] = message

        if metadata:
            response["metadata"] = metadata

        if count is not None:
            response["count"] = count

        return response

    @staticmethod
    def error(
        error: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> JSONResponse:
        """
        Create an error response.

        Args:
            error: Error message
            status_code: HTTP status code
            details: Optional error details
            error_code: Optional application-specific error code

        Returns:
            JSONResponse with error information
        """
        response = {
            "success": False,
            "error": error,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }

        if details:
            response["details"] = details

        if error_code:
            response["error_code"] = error_code

        return JSONResponse(status_code=status_code, content=response)

    @staticmethod
    def paginated(
        data: list[Any],
        page: int,
        page_size: int,
        total: int,
        message: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a paginated response.

        Args:
            data: List of items for current page
            page: Current page number
            page_size: Items per page
            total: Total number of items
            message: Optional message

        Returns:
            Standardized paginated response
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "message": message,
        }


def handle_api_error(
    error: Exception, default_message: str = "An error occurred"
) -> JSONResponse:
    """
    Convert exceptions to standardized error responses.

    Args:
        error: The exception to handle
        default_message: Default error message if none provided

    Returns:
        JSONResponse with error information
    """
    if isinstance(error, HTTPException):
        return APIResponse.error(
            error=error.detail or default_message, status_code=error.status_code
        )

    # Log unexpected errors (in production, use proper logging)
    print(f"Unexpected error: {str(error)}")

    return APIResponse.error(
        error=default_message, status_code=500, details={"type": type(error).__name__}
    )


def sanitize_error_for_api(error: Exception) -> str:
    """
    Sanitize error messages for safe API exposure.

    In production, this should:
    - Remove sensitive information
    - Hide internal implementation details
    - Return user-friendly error messages

    Args:
        error: The exception to sanitize

    Returns:
        Safe error message string
    """
    import os

    # In development, show more details
    if os.getenv("ENVIRONMENT", "production") in ["development", "test"]:
        return str(error)

    # In production, return generic messages based on error type
    error_type = type(error).__name__

    # Map common errors to user-friendly messages
    error_messages = {
        "ValueError": "Invalid input provided",
        "KeyError": "Required data not found",
        "ConnectionError": "Service temporarily unavailable",
        "TimeoutError": "Request timed out",
        "PermissionError": "Access denied",
        "NotImplementedError": "Feature not available",
    }

    # Return mapped message or generic message
    return error_messages.get(error_type, "An error occurred processing your request")


# Response type hints for better IDE support
SuccessResponse = dict[str, Any]
ErrorResponse = JSONResponse
PaginatedResponse = dict[str, Any]


# Example usage functions
def format_list_response(items: list[Any], item_name: str = "items") -> SuccessResponse:
    """Format a list response with count."""
    return APIResponse.success(
        data=items, count=len(items), message=f"Retrieved {len(items)} {item_name}"
    )


def format_single_item_response(item: Any, item_name: str = "item") -> SuccessResponse:
    """Format a single item response."""
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"{item_name.capitalize()} not found"
        )

    return APIResponse.success(
        data=item, message=f"{item_name.capitalize()} retrieved successfully"
    )
