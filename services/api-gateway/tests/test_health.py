"""Health check endpoint tests."""

from fastapi.testclient import TestClient


def test_root_endpoint():
    """Test root endpoint returns expected message."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Diet Issue Tracker API Gateway (Test Mode)",
        "status": "running",
    }


def test_health_endpoint():
    """Test health endpoint returns service status."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "status" in data
    assert data["status"] == "healthy"
    assert "service" in data
    assert data["service"] == "api-gateway"
    assert "environment" in data
    assert "database_configured" in data
    assert "redis_configured" in data
    assert "jwt_configured" in data


def test_env_endpoint():
    """Test environment debug endpoint."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/test/env")

    assert response.status_code == 200
    data = response.json()

    # Check environment variables are reported
    assert "environment" in data
    assert "has_database_url" in data
    assert "has_redis_url" in data
    assert "has_jwt_secret" in data
    assert "has_airtable_key" in data
