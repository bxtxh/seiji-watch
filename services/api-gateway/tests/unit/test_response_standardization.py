"""
Tests for API response standardization.
Verifies that API responses follow the standardized format.
"""

import pytest
from src.utils.response_format import APIResponse, handle_api_error
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import json


class TestResponseStandardization:
    """Test response format utilities."""

    def test_success_response_basic(self):
        """Test basic success response."""
        data = {"id": 1, "name": "Test"}
        response = APIResponse.success(data)

        assert response["success"] is True
        assert response["data"] == data
        assert "timestamp" in response
        assert response["timestamp"].endswith("Z")  # UTC format

    def test_success_response_with_metadata(self):
        """Test success response with all optional fields."""
        data = [{"id": 1}, {"id": 2}]
        metadata = {"source": "airtable", "cached": False}

        response = APIResponse.success(
            data=data, message="Items retrieved", metadata=metadata, count=2
        )

        assert response["success"] is True
        assert response["data"] == data
        assert response["message"] == "Items retrieved"
        assert response["metadata"] == metadata
        assert response["count"] == 2

    def test_error_response(self):
        """Test error response format."""
        response = APIResponse.error(
            error="Validation failed",
            status_code=400,
            details={"field": "email", "reason": "Invalid format"},
            error_code="VALIDATION_ERROR",
        )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

        # Parse the JSON content
        content = json.loads(response.body)
        assert content["success"] is False
        assert content["error"] == "Validation failed"
        assert content["details"]["field"] == "email"
        assert content["error_code"] == "VALIDATION_ERROR"
        assert "timestamp" in content

    def test_paginated_response(self):
        """Test paginated response format."""
        data = [{"id": i} for i in range(1, 21)]

        response = APIResponse.paginated(
            data=data[:10],  # First page
            page=1,
            page_size=10,
            total=20,
            message="First page of results",
        )

        assert response["success"] is True
        assert len(response["data"]) == 10
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["page_size"] == 10
        assert response["pagination"]["total"] == 20
        assert response["pagination"]["total_pages"] == 2
        assert response["pagination"]["has_next"] is True
        assert response["pagination"]["has_prev"] is False

    def test_handle_http_exception(self):
        """Test handling of HTTPException."""
        exc = HTTPException(status_code=404, detail="Resource not found")
        response = handle_api_error(exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

        content = json.loads(response.body)
        assert content["success"] is False
        assert content["error"] == "Resource not found"

    def test_handle_generic_exception(self):
        """Test handling of generic exceptions."""
        exc = ValueError("Invalid value")
        response = handle_api_error(exc, default_message="Operation failed")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        content = json.loads(response.body)
        assert content["success"] is False
        assert content["error"] == "Operation failed"
        assert content["details"]["type"] == "ValueError"

    def test_kanban_response_format(self):
        """Test that kanban endpoint response follows standard format."""
        # Simulate kanban response
        kanban_response = {
            "success": True,
            "data": {
                "stages": {
                    "backlog": [],
                    "in_progress": [
                        {
                            "id": "rec1",
                            "title": "Test Issue",
                            "stage": "in_progress",
                            "schedule": {"from": "2025-07-01", "to": "2025-07-28"},
                            "tags": ["tag1"],
                            "related_bills": [],
                            "updated_at": "2025-07-12T10:00:00Z",
                        }
                    ],
                    "in_review": [],
                    "completed": [],
                }
            },
            "metadata": {
                "total_issues": 1,
                "last_updated": "2025-07-12T10:00:00Z",
                "date_range": {"from": "2025-07-01", "to": "2025-07-28"},
            },
        }

        # Verify it matches our standard format
        assert kanban_response["success"] is True
        assert "data" in kanban_response
        assert "metadata" in kanban_response
        assert "stages" in kanban_response["data"]

    def test_members_response_should_be_standardized(self):
        """Test that members endpoint needs standardization."""
        # Current format (raw array)
        current_response = [
            {"id": "rec1", "fields": {"Name": "田中太郎"}},
            {"id": "rec2", "fields": {"Name": "佐藤花子"}},
        ]

        # Expected standardized format
        expected_response = APIResponse.success(
            data=current_response,
            count=len(current_response),
            message="Members retrieved successfully",
        )

        assert expected_response["success"] is True
        assert expected_response["data"] == current_response
        assert expected_response["count"] == 2
        assert "timestamp" in expected_response

    def test_empty_list_response(self):
        """Test standardized response for empty lists."""
        response = APIResponse.success(data=[], count=0, message="No items found")

        assert response["success"] is True
        assert response["data"] == []
        assert response["count"] == 0
        assert response["message"] == "No items found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
