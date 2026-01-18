"""Core module - security, permissions, exceptions."""

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    get_password_hash,
)
from app.core.permissions import (
    Permission,
    PermissionChecker,
    ResourceAccessChecker,
    ROLE_PERMISSIONS,
    DEPARTMENT_PERMISSIONS,
)
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    BadRequestError,
)

__all__ = [
    # Security
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_password",
    "get_password_hash",
    # Permissions
    "Permission",
    "PermissionChecker",
    "ResourceAccessChecker",
    "ROLE_PERMISSIONS",
    "DEPARTMENT_PERMISSIONS",
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "BadRequestError",
]
