"""
JWT Authentication middleware for API Gateway.
Provides secure authentication for API endpoints.
"""

import os
from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

# Security scheme for JWT Bearer tokens
security = HTTPBearer()


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication on specific routes."""

    def __init__(self, app, secret_key: str, excluded_paths: list = None):
        super().__init__(app)
        self.secret_key = secret_key
        self.excluded_paths = excluded_paths or [
            "/health",
            "/api/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        ]

    async def dispatch(self, request: Request, call_next):
        """Check JWT token for protected routes."""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"},
            )

        # Extract and verify token
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Check token expiration
            if (
                "exp" in payload
                and datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow()
            ):
                return JSONResponse(
                    status_code=401, content={"detail": "Token has expired"}
                )

            # Add user info to request state
            request.state.user = payload

        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Verify JWT token and return payload."""
    token = credentials.credentials
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])

        # Check token expiration
        if (
            "exp" in payload
            and datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow()
        ):
            raise HTTPException(status_code=401, detail="Token has expired")

        return payload

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a new JWT access token."""
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError("JWT_SECRET_KEY not configured")

    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    return jwt.encode(to_encode, secret_key, algorithm="HS256")


# Optional: Role-based access control decorator
def require_role(required_role: str):
    """Decorator to require specific role for endpoint access."""

    def decorator(func):
        async def wrapper(*args, user: dict = Security(verify_token), **kwargs):
            user_role = user.get("role", "")
            if user_role != required_role and user_role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required role: {required_role}",
                )
            return await func(*args, user=user, **kwargs)

        return wrapper

    return decorator
