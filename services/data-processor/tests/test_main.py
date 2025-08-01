"""Main module tests for data processor."""

import pytest


def test_imports():
    """Test that main modules can be imported."""
    try:
        from src import main
        from src.pipeline import data_processor

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")


def test_environment_configuration():
    """Test environment is properly configured."""
    import os

    # Check critical environment variables
    env_vars = ["DATABASE_URL", "REDIS_URL", "ENVIRONMENT"]

    for var in env_vars:
        value = os.getenv(var)
        assert value is not None or var == "REDIS_URL", f"{var} should be configured"
