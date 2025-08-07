"""Authentication tests."""

import pytest
import os


def test_jwt_configuration():
    """Test JWT configuration is properly set."""
    # Since JWT_SECRET_KEY is required, this tests the middleware
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    assert jwt_secret is not None, "JWT_SECRET_KEY must be set"

    # Test algorithm is set
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    assert jwt_algorithm in ["HS256", "RS256"], "Invalid JWT algorithm"


def test_imports():
    """Test that authentication modules can be imported."""
    try:
        from src.middleware import auth

        assert hasattr(auth, "require_admin_access")
    except ImportError as e:
        pytest.fail(f"Failed to import auth module: {e}")


def test_cors_middleware_configured():
    """Test CORS middleware is configured."""
    from src.main import app

    # Check if CORS middleware is in the middleware stack
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in str(
        middleware_classes
    ), "CORS middleware should be configured"
