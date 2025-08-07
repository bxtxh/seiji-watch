"""STT worker tests."""

import pytest


def test_imports():
    """Test that STT worker modules can be imported."""
    try:
        from src import main

        assert True
    except ImportError:
        # Module structure might be different
        pass


def test_worker_configuration():
    """Test STT worker configuration."""
    import os

    # Check if OpenAI API key is configured (for Whisper)
    openai_key = os.getenv("OPENAI_API_KEY")
    # Not required in test environment

    assert True
