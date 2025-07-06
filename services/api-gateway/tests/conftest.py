"""Test configuration and fixtures."""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock


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