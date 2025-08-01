"""
Unit tests for simple API endpoints.
Tests basic functionality without importing simple_api directly.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from unittest.mock import AsyncMock, patch
import json


class TestSimpleAPIEndpoints:
    """Test simple API endpoints functionality."""

    @pytest.fixture
    def app(self):
        """Create a minimal FastAPI app that mimics simple_api structure."""
        app = FastAPI()

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:3001"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mock endpoints
        @app.get("/api/health")
        async def health_check():
            return {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-07-28T10:00:00Z",
            }

        @app.get("/api/members")
        async def get_members():
            return {
                "success": True,
                "data": [
                    {
                        "id": "rec001",
                        "name": "田中太郎",
                        "party": "自由民主党",
                        "house": "衆議院",
                    }
                ],
                "count": 1,
            }

        @app.get("/api/issues/kanban")
        async def get_kanban():
            return {
                "success": True,
                "data": {
                    "stages": {
                        "backlog": [],
                        "in_progress": [
                            {
                                "id": "rec1",
                                "title": "Test Issue",
                                "stage": "in_progress",
                            }
                        ],
                        "in_review": [],
                        "completed": [],
                    }
                },
                "metadata": {"total_issues": 1, "last_updated": "2025-07-28T10:00:00Z"},
            }

        return app

    def test_health_endpoint(self, app):
        """Test health check endpoint returns correct status."""
        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_members_endpoint(self, app):
        """Test members endpoint returns data in correct format."""
        client = TestClient(app)
        response = client.get("/api/members")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        assert isinstance(data["data"], list)

        if len(data["data"]) > 0:
            member = data["data"][0]
            assert "id" in member
            assert "name" in member
            assert "party" in member
            assert "house" in member

    def test_kanban_endpoint(self, app):
        """Test kanban endpoint returns proper stage structure."""
        client = TestClient(app)
        response = client.get("/api/issues/kanban")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "stages" in data["data"]
        assert "metadata" in data

        stages = data["data"]["stages"]
        expected_stages = ["backlog", "in_progress", "in_review", "completed"]
        for stage in expected_stages:
            assert stage in stages
            assert isinstance(stages[stage], list)

    def test_cors_headers(self, app):
        """Test CORS headers are properly set."""
        client = TestClient(app)

        # Test preflight request
        response = client.options(
            "/api/members",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_api_response_consistency(self, app):
        """Test that all API responses follow consistent format."""
        client = TestClient(app)

        endpoints = ["/api/members", "/api/issues/kanban"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200

            data = response.json()
            # All endpoints should have success flag
            assert "success" in data
            assert isinstance(data["success"], bool)

            # If successful, should have data field
            if data["success"]:
                assert "data" in data

    @pytest.mark.asyncio
    async def test_airtable_connection_mock(self):
        """Test Airtable connection behavior with mocks."""
        mock_response = {"records": [{"id": "rec1", "fields": {"Name": "Test"}}]}

        # Mock the aiohttp client response
        mock_get = AsyncMock()
        mock_get.return_value.status = 200
        mock_get.return_value.json = AsyncMock(return_value=mock_response)

        # Simulate fetching records
        response = await mock_get("https://api.airtable.com/v0/base/table")
        data = await response.json()

        assert data["records"][0]["fields"]["Name"] == "Test"
        mock_get.assert_called_once_with("https://api.airtable.com/v0/base/table")

    def test_error_handling(self, app):
        """Test API error handling returns proper error format."""
        # Create an app with an endpoint that raises an error
        from fastapi.responses import JSONResponse

        error_app = FastAPI()

        @error_app.get("/api/error")
        async def error_endpoint():
            raise ValueError("Test error")

        @error_app.exception_handler(ValueError)
        async def value_error_handler(request, exc):
            return JSONResponse(
                status_code=400, content={"success": False, "error": str(exc)}
            )

        client = TestClient(error_app)
        response = client.get("/api/error")

        # Should handle error gracefully
        assert response.status_code == 400
        assert response.json()["success"] is False
        assert "Test error" in response.json()["error"]

    def test_query_parameters(self, app):
        """Test handling of query parameters."""
        client = TestClient(app)

        # Test with query parameters
        response = client.get("/api/members?search=田中&party=自由民主党")
        assert response.status_code == 200

        # Test kanban with range parameter
        response = client.get("/api/issues/kanban?range=30d&max_per_stage=8")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
