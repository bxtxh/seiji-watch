"""Authentication and authorization for migration operations."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = __import__("logging").getLogger(__name__)


class Role(Enum):
    """User roles for migration operations."""

    ADMIN = "admin"  # Full access to all operations
    OPERATOR = "operator"  # Can run migrations and sync
    VIEWER = "viewer"  # Read-only access to monitoring
    SERVICE = "service"  # Service account for automated operations


class Permission(Enum):
    """Granular permissions for migration operations."""

    # Migration permissions
    MIGRATION_READ = "migration:read"
    MIGRATION_EXECUTE = "migration:execute"
    MIGRATION_ROLLBACK = "migration:rollback"

    # Sync permissions
    SYNC_READ = "sync:read"
    SYNC_START = "sync:start"
    SYNC_STOP = "sync:stop"

    # Monitoring permissions
    MONITORING_READ = "monitoring:read"
    MONITORING_ALERTS = "monitoring:alerts"

    # Admin permissions
    ADMIN_CONFIG = "admin:config"
    ADMIN_USERS = "admin:users"
    ADMIN_ROLLBACK = "admin:rollback"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],  # All permissions
    Role.OPERATOR: [
        Permission.MIGRATION_READ,
        Permission.MIGRATION_EXECUTE,
        Permission.SYNC_READ,
        Permission.SYNC_START,
        Permission.SYNC_STOP,
        Permission.MONITORING_READ,
    ],
    Role.VIEWER: [
        Permission.MIGRATION_READ,
        Permission.SYNC_READ,
        Permission.MONITORING_READ,
    ],
    Role.SERVICE: [
        Permission.MIGRATION_READ,
        Permission.MIGRATION_EXECUTE,
        Permission.SYNC_READ,
        Permission.SYNC_START,
        Permission.MONITORING_READ,
    ],
}


@dataclass
class User:
    """User model for migration operations."""

    id: str
    email: str
    role: Role
    permissions: list[Permission]
    is_active: bool = True
    created_at: datetime = None
    last_login: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def can_execute_migration(self) -> bool:
        """Check if user can execute migrations."""
        return self.has_permission(Permission.MIGRATION_EXECUTE)

    def can_rollback(self) -> bool:
        """Check if user can perform rollbacks."""
        return self.has_permission(
            Permission.MIGRATION_ROLLBACK
        ) or self.has_permission(Permission.ADMIN_ROLLBACK)


class MigrationAuth:
    """Authentication manager for migration operations."""

    def __init__(
        self,
        jwt_secret: str | None = None,
        jwt_algorithm: str = "HS256",
        token_expiry_hours: int = 24,
    ):
        """Initialize authentication manager.

        Args:
            jwt_secret: Secret key for JWT tokens
            jwt_algorithm: JWT signing algorithm
            token_expiry_hours: Token expiration time in hours
        """
        self.jwt_secret = jwt_secret or os.getenv("MIGRATION_JWT_SECRET")
        if not self.jwt_secret:
            # Generate a secure random secret if not provided
            self.jwt_secret = secrets.token_urlsafe(32)
            logger.warning("No JWT secret provided, using generated secret")

        self.jwt_algorithm = jwt_algorithm
        self.token_expiry_hours = token_expiry_hours

        # In-memory user store (in production, use database)
        self.users: dict[str, User] = {}

        # API key store for service accounts
        self.api_keys: dict[str, str] = {}  # key_hash -> user_id

        # Initialize default admin user
        self._init_default_admin()

    def _init_default_admin(self):
        """Initialize default admin user."""
        admin_email = os.getenv("MIGRATION_ADMIN_EMAIL", "admin@seiji-watch.jp")
        admin_password = os.getenv("MIGRATION_ADMIN_PASSWORD")

        if not admin_password:
            # 🔴 認証情報が必要です
            logger.error(
                "MIGRATION_ADMIN_PASSWORD environment variable not set. "
                "Please set it to secure the migration system."
            )
            admin_password = "changeme"  # Default password for development

        admin_user = User(
            id="admin",
            email=admin_email,
            role=Role.ADMIN,
            permissions=ROLE_PERMISSIONS[Role.ADMIN],
        )

        self.users[admin_user.id] = admin_user

        # Store password hash (in production, use bcrypt)
        self.password_hashes = {admin_user.id: self._hash_password(admin_password)}

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt for secure password storage."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def create_user(self, email: str, password: str, role: Role = Role.VIEWER) -> User:
        """Create a new user.

        Args:
            email: User email
            password: User password
            role: User role

        Returns:
            Created user
        """
        user_id = f"user_{len(self.users) + 1}"

        user = User(
            id=user_id, email=email, role=role, permissions=ROLE_PERMISSIONS[role]
        )

        self.users[user_id] = user
        self.password_hashes[user_id] = self._hash_password(password)

        logger.info(f"Created user: {email} with role {role.value}")

        return user

    def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            Authenticated user or None
        """
        # Find user by email
        user = next((u for u in self.users.values() if u.email == email), None)

        if not user or not user.is_active:
            return None

        # Verify password
        stored_hash = self.password_hashes.get(user.id)
        if not stored_hash:
            return None

        # Use bcrypt's checkpw for secure comparison
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return None

        # Update last login
        user.last_login = datetime.utcnow()

        return user

    def create_token(self, user: User) -> str:
        """Create JWT token for user.

        Args:
            user: User to create token for

        Returns:
            JWT token
        """
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
            "permissions": [p.value for p in user.permissions],
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        return token

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token.

        Args:
            token: JWT token

        Returns:
            Decoded token payload or None
        """
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def create_api_key(self, user_id: str, description: str = "") -> str:
        """Create API key for service account.

        Args:
            user_id: User ID to create key for
            description: Key description

        Returns:
            API key
        """
        user = self.users.get(user_id)
        if not user or user.role != Role.SERVICE:
            raise ValueError("API keys can only be created for service accounts")

        # Generate secure random key
        api_key = f"mig_{secrets.token_urlsafe(32)}"

        # Store hash of key using bcrypt
        salt = bcrypt.gensalt()
        key_hash = bcrypt.hashpw(api_key.encode("utf-8"), salt).decode("utf-8")
        self.api_keys[key_hash] = user_id

        logger.info(f"Created API key for user {user_id}: {description}")

        # 🔴 認証情報が必要です - APIキーを安全に保存してください
        logger.warning(
            f"Store this API key securely, it won't be shown again: {api_key}"
        )

        return api_key

    def verify_api_key(self, api_key: str) -> User | None:
        """Verify API key and return associated user.

        Args:
            api_key: API key to verify

        Returns:
            User associated with key or None
        """
        # Check against all stored API key hashes
        for stored_hash, user_id in self.api_keys.items():
            if bcrypt.checkpw(api_key.encode("utf-8"), stored_hash.encode("utf-8")):
                return self.users.get(user_id)

        return None


# FastAPI dependencies
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """FastAPI dependency to get current authenticated user.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    auth = MigrationAuth()

    token = credentials.credentials

    # Try as JWT token first
    payload = auth.verify_token(token)
    if payload:
        user_id = payload.get("sub")
        user = auth.users.get(user_id)
        if user and user.is_active:
            return user

    # Try as API key
    user = auth.verify_api_key(token)
    if user and user.is_active:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: Permission):
    """FastAPI dependency to require specific permission.

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """

    async def permission_checker(user: User = Depends(get_current_user)):
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return user

    return permission_checker


def require_role(role: Role):
    """FastAPI dependency to require specific role.

    Args:
        role: Required role

    Returns:
        Dependency function
    """

    async def role_checker(user: User = Depends(get_current_user)):
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}",
            )
        return user

    return role_checker


class MigrationAudit:
    """Audit logging for migration operations."""

    def __init__(self):
        self.audit_log: list[dict[str, Any]] = []

    def log_operation(
        self,
        user: User,
        operation: str,
        target: str,
        status: str,
        details: dict[str, Any] | None = None,
    ):
        """Log a migration operation.

        Args:
            user: User performing operation
            operation: Operation type
            target: Target of operation
            status: Operation status
            details: Additional details
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user.id,
            "user_email": user.email,
            "operation": operation,
            "target": target,
            "status": status,
            "details": details or {},
        }

        self.audit_log.append(entry)

        logger.info(f"AUDIT: {user.email} performed {operation} on {target} - {status}")

    def get_audit_log(
        self, user_id: str | None = None, operation: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get audit log entries.

        Args:
            user_id: Filter by user ID
            operation: Filter by operation
            limit: Maximum entries to return

        Returns:
            Audit log entries
        """
        logs = self.audit_log

        if user_id:
            logs = [l for l in logs if l["user_id"] == user_id]

        if operation:
            logs = [l for l in logs if l["operation"] == operation]

        # Return most recent first
        return logs[-limit:][::-1]
