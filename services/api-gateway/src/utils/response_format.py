"""
Standardized API response format utilities.
Ensures consistent response structure across all endpoints.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class APIResponse:
    """Standardized API response formatter."""

    @staticmethod
    def success(
        data: Any,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        count: Optional[int] = None,
    ) -> Dict[str, Any]:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if details:
            response["details"] = details

        if error_code:
            response["error_code"] = error_code

        return JSONResponse(status_code=status_code, content=response)

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        page_size: int,
        total: int,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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


# Response type hints for better IDE support
SuccessResponse = Dict[str, Any]
ErrorResponse = JSONResponse
PaginatedResponse = Dict[str, Any]


# Example usage functions
def format_list_response(items: List[Any], item_name: str = "items") -> SuccessResponse:
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
