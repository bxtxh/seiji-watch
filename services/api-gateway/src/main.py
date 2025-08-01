"""
Simple test main.py for Docker environment testing.
This version includes only essential health check functionality.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI instance
app = FastAPI(
    title="Diet Issue Tracker API (Test Mode)",
    description="API Gateway for Diet Issue Tracker - Test Mode",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Diet Issue Tracker API Gateway (Test Mode)",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "database_configured": bool(os.getenv("DATABASE_URL")),
        "redis_configured": bool(os.getenv("REDIS_URL")),
        "jwt_configured": bool(os.getenv("JWT_SECRET_KEY")),
    }


@app.get("/test/env")
async def test_env():
    """Test environment variables (for debugging)."""
    return {
        "environment": os.getenv("ENVIRONMENT"),
        "has_database_url": bool(os.getenv("DATABASE_URL")),
        "has_redis_url": bool(os.getenv("REDIS_URL")),
        "has_jwt_secret": bool(os.getenv("JWT_SECRET_KEY")),
        "has_airtable_key": bool(os.getenv("AIRTABLE_API_KEY")),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
