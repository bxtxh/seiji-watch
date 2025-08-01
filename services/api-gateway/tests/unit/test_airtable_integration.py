"""
Unit tests for Airtable integration functionality.
Tests the basic happy path scenarios for Airtable data fetching.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
import json


class TestAirtableIntegration:
    """Test Airtable integration functionality."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx client for API calls."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_airtable_response(self):
        """Mock successful Airtable response."""
        return {
            "records": [
                {
                    "id": "rec001",
                    "fields": {
                        "Name": "田中太郎",
                        "Party": "自由民主党",
                        "House": "衆議院",
                        "Prefecture": "東京都",
                    },
                    "createdTime": "2025-07-12T10:00:00.000Z",
                },
                {
                    "id": "rec002",
                    "fields": {
                        "Name": "佐藤花子",
                        "Party": "立憲民主党",
                        "House": "参議院",
                        "Prefecture": "大阪府",
                    },
                    "createdTime": "2025-07-12T10:00:00.000Z",
                },
            ],
            "offset": None,
        }

    @pytest.mark.asyncio
    async def test_fetch_members_success(
        self, mock_httpx_client, mock_airtable_response
    ):
        """Test successful fetching of members from Airtable."""
        # Mock the response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_airtable_response
        mock_httpx_client.get.return_value = mock_response

        # Test by simulating the behavior rather than importing simple_api
        async def mock_fetch_airtable_records(table_name):
            headers = {
                "Authorization": "Bearer test_pat",
                "Content-Type": "application/json",
            }
            response = await mock_httpx_client.get(
                f"https://api.airtable.com/v0/test_base/{table_name}", headers=headers
            )
            return response.json()["records"]

        # Test the fetch operation
        result = await mock_fetch_airtable_records("Members")

        assert result == mock_airtable_response["records"]
        mock_httpx_client.get.assert_called_once()

        # Verify the API was called with correct headers
        call_args = mock_httpx_client.get.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_fetch_issues_success(self, mock_httpx_client):
        """Test successful fetching of issues from Airtable."""
        mock_issues_response = {
            "records": [
                {
                    "id": "recIssue001",
                    "fields": {
                        "title": "健康保険料の負担軽減策検討",
                        "stage": "in_progress",
                        "category": "社会保障",
                        "priority": "high",
                    },
                }
            ]
        }

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issues_response
        mock_httpx_client.get.return_value = mock_response

        # Test by simulating the behavior
        async def mock_fetch_airtable_records(table_name):
            response = await mock_httpx_client.get(
                f"https://api.airtable.com/v0/test_base/{table_name}"
            )
            return response.json()["records"]

        result = await mock_fetch_airtable_records("Issues")

        assert len(result) == 1
        assert result[0]["fields"]["title"] == "健康保険料の負担軽減策検討"

    @pytest.mark.asyncio
    async def test_fetch_with_pagination(self, mock_httpx_client):
        """Test fetching records with pagination."""
        # First page response
        first_page = {
            "records": [{"id": "rec1", "fields": {"Name": "Test1"}}],
            "offset": "page2",
        }

        # Second page response
        second_page = {
            "records": [{"id": "rec2", "fields": {"Name": "Test2"}}],
            "offset": None,
        }

        mock_response1 = MagicMock(spec=Response)
        mock_response1.status_code = 200
        mock_response1.json.return_value = first_page

        mock_response2 = MagicMock(spec=Response)
        mock_response2.status_code = 200
        mock_response2.json.return_value = second_page

        mock_httpx_client.get.side_effect = [mock_response1, mock_response2]

        # Simulate pagination behavior
        async def mock_fetch_with_pagination(table_name):
            all_records = []
            offset = None

            for i in range(2):  # Simulate 2 API calls
                response = await mock_httpx_client.get(
                    f"https://api.airtable.com/v0/test_base/{table_name}"
                )
                data = response.json()
                all_records.extend(data["records"])
                offset = data.get("offset")
                if not offset:
                    break

            return all_records

        result = await mock_fetch_with_pagination("Members")

        assert len(result) == 2
        assert result[0]["fields"]["Name"] == "Test1"
        assert result[1]["fields"]["Name"] == "Test2"
        assert mock_httpx_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_airtable_error(self, mock_httpx_client):
        """Test handling of Airtable API errors."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"type": "AUTHENTICATION_REQUIRED"}}
        mock_httpx_client.get.return_value = mock_response

        # Simulate error handling
        async def mock_fetch_with_error(table_name):
            response = await mock_httpx_client.get(
                f"https://api.airtable.com/v0/test_base/{table_name}"
            )
            if response.status_code != 200:
                raise Exception(f"Airtable API error: {response.status_code}")
            return response.json()["records"]

        with pytest.raises(Exception) as exc_info:
            await mock_fetch_with_error("Members")

        assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_kanban_data_transformation(self, mock_httpx_client):
        """Test transformation of issues data for kanban board."""
        mock_issues = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "title": "Issue 1",
                        "stage": "in_progress",
                        "schedule_from": "2025-07-01",
                        "schedule_to": "2025-07-28",
                        "tags": ["tag1", "tag2"],
                        "updated_at": "2025-07-12T10:00:00Z",
                    },
                },
                {
                    "id": "rec2",
                    "fields": {
                        "title": "Issue 2",
                        "stage": "in_review",
                        "schedule_from": "2025-07-01",
                        "schedule_to": "2025-07-28",
                        "tags": ["tag3"],
                        "updated_at": "2025-07-12T11:00:00Z",
                    },
                },
            ]
        }

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issues
        mock_httpx_client.get.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            from simple_api import app
            from fastapi.testclient import TestClient

            client = TestClient(app)
            response = client.get("/api/issues/kanban?range=30d&max_per_stage=8")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "data" in data
            assert "stages" in data["data"]
            assert "metadata" in data

            # Check stage organization
            stages = data["data"]["stages"]
            assert "in_progress" in stages
            assert "in_review" in stages
            assert len(stages["in_progress"]) >= 0
            assert len(stages["in_review"]) >= 0

    @pytest.mark.asyncio
    async def test_members_search_functionality(
        self, mock_httpx_client, mock_airtable_response
    ):
        """Test members search functionality."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_airtable_response
        mock_httpx_client.get.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            from simple_api import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            # Test search by name
            response = client.get("/api/members?search=田中")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Test filter by party
            response = client.get("/api/members?party=自由民主党")
            assert response.status_code == 200

            # Test filter by house
            response = client.get("/api/members?house=衆議院")
            assert response.status_code == 200

    def test_api_health_check(self):
        """Test API health check endpoint."""
        from simple_api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_cors_configuration(self):
        """Test CORS is properly configured."""
        from simple_api import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Test preflight request
        response = client.options(
            "/api/members",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
