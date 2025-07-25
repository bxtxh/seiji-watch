"""
Shared test configuration and fixtures for Policy Issue Extraction tests.
Provides common fixtures, mocks, and test utilities.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Test environment configuration
os.environ.update(
    {
        "OPENAI_API_KEY": "test_openai_key",
        "AIRTABLE_API_KEY": "test_airtable_key",
        "AIRTABLE_BASE_ID": "test_base_id",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "DISCORD_NOTIFICATIONS_ENABLED": "false",  # Disable for tests
        "LOG_LEVEL": "INFO",
    }
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client with typical responses."""
    mock_client = AsyncMock()

    # Default successful response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps(
        {
            "label_lv1": "政策課題を解決する",
            "label_lv2": "包括的な政策課題の解決を図る",
            "confidence": 0.85,
        }
    )

    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_airtable_client():
    """Create a mock Airtable client with typical responses."""
    mock_client = AsyncMock()
    mock_client.base_url = "https://api.airtable.com/v0/test_base"

    # Default successful response
    mock_client._rate_limited_request.return_value = {
        "id": "rec_test_123",
        "fields": {},
        "createdTime": datetime.now().isoformat(),
    }

    mock_client.health_check.return_value = True
    return mock_client


@pytest.fixture
def mock_discord_client():
    """Create a mock Discord client."""
    mock_client = AsyncMock()

    # Mock successful webhook response
    mock_response = AsyncMock()
    mock_response.status = 204
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession", return_value=mock_session):
        yield mock_client


@pytest.fixture
def sample_bill_data():
    """Create sample bill data for testing."""
    from services.policy_issue_extractor import BillData

    return BillData(
        id="test_bill_001",
        title="介護保険制度改正法案",
        outline="高齢者の介護負担を軽減し、制度の持続可能性を確保する",
        background_context="高齢化社会の進展により介護需要が増加している",
        expected_effects="介護費用の削減と質の向上が期待される",
        key_provisions=["自己負担率の見直し", "サービス提供体制の強化"],
        submitter="厚生労働省",
        category="社会保障",
    )


@pytest.fixture
def sample_dual_issue():
    """Create sample dual-level issue for testing."""
    from services.policy_issue_extractor import DualLevelIssue

    return DualLevelIssue(
        label_lv1="介護制度を改善する",
        label_lv2="高齢者介護保険制度の包括的な見直しを実施する",
        confidence=0.85,
    )


@pytest.fixture
def sample_issue_record():
    """Create sample issue record for testing."""
    from services.airtable_issue_manager import AirtableIssueRecord

    return AirtableIssueRecord(
        issue_id=str(uuid.uuid4()),
        label_lv1="テスト政策課題",
        label_lv2="詳細なテスト政策課題",
        confidence=0.8,
        status="pending",
        source_bill_id="test_bill_001",
        quality_score=0.75,
    )


@pytest.fixture
def mock_all_components(mock_openai_client, mock_airtable_client, mock_discord_client):
    """Provide all mocked components together."""
    return {
        "openai_client": mock_openai_client,
        "airtable_client": mock_airtable_client,
        "discord_client": mock_discord_client,
    }


# Custom pytest markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line(
        "markers", "integration: Integration tests for workflow testing"
    )
    config.addinivalue_line("markers", "performance: Performance and scalability tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
    config.addinivalue_line(
        "markers", "requires_api: Tests that require external API access"
    )
    config.addinivalue_line(
        "markers", "requires_db: Tests that require database access"
    )


# Test data factories
class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_bill_data(**kwargs):
        """Create test bill data with defaults."""
        from services.policy_issue_extractor import BillData

        defaults = {
            "id": f"bill_{uuid.uuid4().hex[:8]}",
            "title": "テスト法案",
            "outline": "法案の概要説明",
            "background_context": "背景コンテキスト",
            "expected_effects": "期待される効果",
            "key_provisions": ["条項1", "条項2"],
            "submitter": "提出者",
            "category": "テスト",
        }
        defaults.update(kwargs)
        return BillData(**defaults)

    @staticmethod
    def create_dual_issue(**kwargs):
        """Create test dual-level issue with defaults."""
        from services.policy_issue_extractor import DualLevelIssue

        defaults = {
            "label_lv1": "政策課題を解決する",
            "label_lv2": "包括的な政策課題の解決を図る",
            "confidence": 0.8,
        }
        defaults.update(kwargs)
        return DualLevelIssue(**defaults)

    @staticmethod
    def create_issue_record(**kwargs):
        """Create test issue record with defaults."""
        from services.airtable_issue_manager import AirtableIssueRecord

        defaults = {
            "issue_id": str(uuid.uuid4()),
            "label_lv1": "テスト政策課題",
            "label_lv2": "詳細なテスト政策課題",
            "confidence": 0.8,
            "status": "pending",
            "source_bill_id": f"bill_{uuid.uuid4().hex[:8]}",
            "quality_score": 0.75,
        }
        defaults.update(kwargs)
        return AirtableIssueRecord(**defaults)

    @staticmethod
    def create_airtable_response(records_data):
        """Create mock Airtable API response."""
        return {
            "records": [
                {
                    "id": f"rec_{i}",
                    "fields": record_data,
                    "createdTime": datetime.now().isoformat(),
                }
                for i, record_data in enumerate(records_data)
            ]
        }

    @staticmethod
    def create_openai_response(content):
        """Create mock OpenAI API response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = content
        return mock_response


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory


# Async test utilities
class AsyncTestUtils:
    """Utilities for async testing."""

    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """Wait for a condition to become true."""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)

        return False

    @staticmethod
    async def run_with_timeout(coro, timeout=10.0):
        """Run a coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)


@pytest.fixture
def async_test_utils():
    """Provide async test utilities."""
    return AsyncTestUtils


# Performance testing utilities
class PerformanceTracker:
    """Track performance metrics during tests."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.metrics = {}

    def start(self):
        """Start performance tracking."""
        self.start_time = asyncio.get_event_loop().time()

    def stop(self):
        """Stop performance tracking."""
        self.end_time = asyncio.get_event_loop().time()

    @property
    def duration(self):
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def add_metric(self, name, value):
        """Add a custom metric."""
        self.metrics[name] = value

    def get_summary(self):
        """Get performance summary."""
        summary = {"duration_seconds": self.duration, "metrics": self.metrics}
        return summary


@pytest.fixture
def performance_tracker():
    """Provide performance tracker."""
    return PerformanceTracker()


# Mock validators for testing
class MockValidators:
    """Mock validators for testing without external dependencies."""

    @staticmethod
    def mock_verb_ending_validator():
        """Mock verb ending validator that always returns True."""
        with patch(
            "services.policy_issue_extractor.VerbEndingValidator.is_valid_verb_ending",
            return_value=True,
        ):
            yield

    @staticmethod
    def mock_vocabulary_validator():
        """Mock vocabulary validator that always returns True."""
        with patch(
            "services.policy_issue_extractor.VocabularyLevelValidator.is_high_school_appropriate",
            return_value=True,
        ):
            yield


@pytest.fixture
def mock_validators():
    """Provide mock validators."""
    return MockValidators


# Test database setup (for integration tests)
@pytest.fixture
async def test_database():
    """Setup test database for integration tests."""
    # This would setup a test database if needed
    # For now, we're using mocks
    pass


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_environment():
    """Cleanup test environment after each test."""
    yield
    # Cleanup any test artifacts
    # Clear any global state
    # Reset environment variables if modified


# Custom assertions
class CustomAssertions:
    """Custom assertions for testing specific scenarios."""

    @staticmethod
    def assert_valid_dual_issue(issue):
        """Assert that a dual-level issue is valid."""
        assert hasattr(issue, "label_lv1")
        assert hasattr(issue, "label_lv2")
        assert hasattr(issue, "confidence")
        assert 10 <= len(issue.label_lv1) <= 60
        assert 10 <= len(issue.label_lv2) <= 60
        assert 0.0 <= issue.confidence <= 1.0

    @staticmethod
    def assert_valid_issue_record(record):
        """Assert that an issue record is valid."""
        assert hasattr(record, "issue_id")
        assert hasattr(record, "label_lv1")
        assert hasattr(record, "label_lv2")
        assert hasattr(record, "status")
        assert record.status in ["pending", "approved", "rejected", "failed_validation"]

    @staticmethod
    def assert_performance_acceptable(duration, max_duration):
        """Assert that performance is acceptable."""
        assert (
            duration <= max_duration
        ), f"Performance not acceptable: {duration}s > {max_duration}s"


@pytest.fixture
def custom_assertions():
    """Provide custom assertions."""
    return CustomAssertions


# Test skip conditions
def skip_if_no_api_key():
    """Skip test if no API key is available."""
    return pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY") == "test_openai_key",
        reason="No real OpenAI API key available",
    )


def skip_if_no_network():
    """Skip test if no network connection is available."""
    import socket

    def has_network():
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    return pytest.mark.skipif(
        not has_network(), reason="No network connection available"
    )


# Export commonly used fixtures and utilities
__all__ = [
    "mock_openai_client",
    "mock_airtable_client",
    "mock_discord_client",
    "sample_bill_data",
    "sample_dual_issue",
    "sample_issue_record",
    "test_data_factory",
    "async_test_utils",
    "performance_tracker",
    "mock_validators",
    "custom_assertions",
    "skip_if_no_api_key",
    "skip_if_no_network",
]
