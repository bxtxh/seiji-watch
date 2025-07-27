"""
Authentication Middleware
Implements JWT-based authentication as specified in CLAUDE.md
"""

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# JWT Configuration - SECURITY: No fallback secrets allowed
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Security check: JWT_SECRET_KEY is required in all environments
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable must be set. "
        "This is required for security - no fallback secrets allowed."
    )

# Security scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error."""

    pass


def create_access_token(user_id: str, email: str, scopes: list = None) -> str:
    """Create a JWT access token."""
    if scopes is None:
        scopes = ["read"]

    payload = {
        "user_id": user_id,
        "email": email,
        "scopes": scopes,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
        "type": "access_token",
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Check token type
        if payload.get("type") != "access_token":
            raise AuthenticationError("Invalid token type")

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise AuthenticationError("Token has expired")

        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token."""
    try:
        payload = verify_token(credentials.credentials)
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "scopes": payload.get("scopes", []),
        }
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict | None:
    """Get current user if token is provided, otherwise return None."""
    if not credentials:
        # In testing environment, allow API_BEARER_TOKEN as fallback
        if os.getenv("ENVIRONMENT") == "testing":
            api_token = os.getenv("API_BEARER_TOKEN")
            if api_token:
                try:
                    # Create a mock credentials object
                    from fastapi.security import HTTPAuthorizationCredentials

                    mock_credentials = HTTPAuthorizationCredentials(
                        scheme="Bearer", credentials=api_token
                    )
                    return await get_current_user(mock_credentials)
                except Exception:
                    pass
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_scopes(*required_scopes: str):
    """Decorator to require specific scopes."""

    def decorator(user: dict = Depends(get_current_user)):
        user_scopes = user.get("scopes", [])

        for scope in required_scopes:
            if scope not in user_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scope: {scope}",
                )
        return user

    return decorator


# Common scope requirements


async def require_read_access(user: dict = Depends(get_current_user)) -> dict:
    """Require read access."""
    user_scopes = user.get("scopes", [])
    if "read" not in user_scopes and "admin" not in user_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Read access required"
        )
    return user


async def require_write_access(user: dict = Depends(get_current_user)) -> dict:
    """Require write access."""
    user_scopes = user.get("scopes", [])
    if "write" not in user_scopes and "admin" not in user_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Write access required"
        )
    return user


async def require_admin_access(user: dict = Depends(get_current_user)) -> dict:
    """Require admin access."""
    user_scopes = user.get("scopes", [])
    if "admin" not in user_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


# API Key authentication for internal services
API_KEYS = {
    os.getenv("INTERNAL_API_KEY", "internal-service-key"): "internal_service",
    os.getenv("WEBHOOK_API_KEY", "webhook-service-key"): "webhook_service",
}


async def verify_api_key(api_key: str = Depends(HTTPBearer())) -> str:
    """Verify API key for internal service communication."""
    key = api_key.credentials if hasattr(api_key, "credentials") else api_key

    if key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return API_KEYS[key]


# Rate limiting decorator

# PRODUCTION WARNING: Simple in-memory rate limiter doesn't scale
# TODO: Replace with Redis-based implementation for production deployment
# This implementation loses data on restart and doesn't work with multiple instances
request_counts = defaultdict(list)


def rate_limit(max_requests: int, window_seconds: int):
    """Rate limiting decorator."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user identifier
            user = kwargs.get("current_user") or kwargs.get("user")
            if user:
                user_id = user.get("user_id", "anonymous")
            else:
                user_id = "anonymous"

            current_time = time.time()

            # Clean old requests
            request_counts[user_id] = [
                req_time
                for req_time in request_counts[user_id]
                if current_time - req_time < window_seconds
            ]

            # Check rate limit
            if len(request_counts[user_id]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )

            # Record request
            request_counts[user_id].append(current_time)

            return await func(*args, **kwargs)

        return wrapper

    return decorator
