"""Test configuration and fixtures."""

import asyncio
import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("AIRTABLE_API_KEY", "test-airtable-key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test-base-id")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-unified-for-ci-cd")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("API_BEARER_TOKEN", "test-api-bearer-token")


@pytest.fixture
def mock_airtable_client():
    """Mock Airtable client for testing."""
    client = AsyncMock()
    client.health_check.return_value = True
    client.get_speech.return_value = {
        "id": "test-speech-id",
        "fields": {
            "Original_Text": "テスト発言です。",
            "Speaker_Name": "テスト議員",
            "Summary": None,
            "Topics": None,
            "Is_Processed": False
        }
    }
    client.list_speeches.return_value = [
        {
            "id": "test-speech-id",
            "fields": {
                "Original_Text": "テスト発言です。",
                "Speaker_Name": "テスト議員",
                "Summary": "テスト要約",
                "Topics": "トピック1,トピック2",
                "Is_Processed": True
            }
        }
    ]
    return client


@pytest.fixture
def test_token():
    """Generate a test JWT token for authenticated requests."""
    from src.utils.test_auth import generate_test_token
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-unified-for-ci-cd'
    return generate_test_token()


@pytest.fixture
def auth_headers(test_token):
    """Get authorization headers for authenticated requests."""
    from src.utils.test_auth import get_auth_headers
    return get_auth_headers(test_token)


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    os.environ['ENVIRONMENT'] = 'testing'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-unified-for-ci-cd'

    try:
        from src.main import app
        return TestClient(app)
    except ImportError:
        # Return a mock client if app is not available
        return AsyncMock()


@pytest.fixture
def authenticated_client(client, auth_headers):
    """Create a test client with authentication headers pre-configured."""
    if hasattr(client, 'headers'):
        client.headers.update(auth_headers)
    return client
