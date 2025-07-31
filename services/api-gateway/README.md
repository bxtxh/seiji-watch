# API Gateway Service

RESTful API gateway for the Diet Issue Tracker platform.

## Overview

This service provides:

- RESTful API endpoints for all client interactions
- JWT-based authentication and authorization
- Rate limiting and request validation
- CORS configuration for frontend access
- Integration with all backend microservices

## Tech Stack

- Python 3.11+
- FastAPI for high-performance async API
- Redis for caching and rate limiting
- JWT for authentication tokens
- PostgreSQL for data persistence

## API Endpoints

### Issues API

- `GET /api/issues` - List all issues with filtering
- `GET /api/issues/{id}` - Get specific issue details
- `GET /api/issues/categories` - Get issue categories hierarchy
- `GET /api/issues/categories/tree` - Full category tree
- `GET /api/issues/categories/{id}/children` - Child categories

### Bills API

- `GET /api/bills` - List bills with filtering
- `GET /api/bills/{id}` - Get bill details
- `GET /api/bills/{id}/speeches` - Related speeches

### Search API

- `GET /api/search` - Semantic search across content
- `GET /api/search/bills` - Search bills
- `GET /api/search/speeches` - Search speeches

### Authentication API

- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/auth/logout` - Logout

## Directory Structure

```
api-gateway/
├── src/
│   ├── main.py         # FastAPI application entry
│   ├── routes/         # API endpoint definitions
│   ├── middleware/     # Authentication, CORS, rate limiting
│   ├── models/         # Pydantic models
│   └── services/       # Business logic layer
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
└── scripts/            # Utility scripts
```

## Configuration

Environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `CORS_ORIGINS` - Allowed CORS origins

See `pyproject.toml` for dependencies.

## Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn src.main:app --reload --port 8000

# Run tests
poetry run pytest

# Run linting
ruff check .
ruff format .

# Type checking
poetry run mypy .
```

## API Documentation

When running locally, API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI schema: http://localhost:8000/openapi.json
