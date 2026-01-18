"""API Dependencies - Authentication, Authorization, Database Session."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.enums import UserRole, StaffDepartment
from app.core.security import decode_token
from app.core.permissions import Permission, PermissionChecker
from app.core.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    AuthorizationError,
    PermissionDeniedError,
)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract and validate token from Authorization header."""
    if not credentials:
        raise AuthenticationError(message="Authorization header missing")

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError(message="Invalid authentication scheme")

    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    # Decode token
    payload = decode_token(token)
    if not payload:
        raise InvalidTokenError()

    # Check token type
    token_type = payload.get("type")
    if token_type != "access":
        raise InvalidTokenError(message="Invalid token type")

    # Get user ID from token
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError(message="Invalid token payload")

    # Fetch user with profiles
    stmt = (
        select(User)
        .options(
            selectinload(User.doctor_profile),
            selectinload(User.staff_profile),
            selectinload(User.patient_profile),
        )
        .where(User.id == UUID(user_id))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError(message="User not found")

    if not user.is_active:
        raise AuthenticationError(message="User account is inactive")

    if user.deleted_at:
        raise AuthenticationError(message="User account has been deleted")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active (alias for get_current_user with explicit check)."""
    if not current_user.is_active:
        raise AuthorizationError(message="Inactive user")
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        stmt = (
            select(User)
            .options(
                selectinload(User.doctor_profile),
                selectinload(User.staff_profile),
                selectinload(User.patient_profile),
            )
            .where(User.id == UUID(user_id))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.is_active and not user.deleted_at:
            return user

    except Exception:
        pass

    return None


# ==========================================
# ROLE-BASED DEPENDENCIES
# ==========================================


def require_roles(*roles: UserRole):
    """
    Dependency factory for role-based access.

    Usage:
        @router.post("/doctors")
        async def create_doctor(
            current_user: User = Depends(require_roles(UserRole.ADMIN))
        ):
            ...
    """
    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise AuthorizationError(
                message=f"Access denied. Required roles: {[r.value for r in roles]}"
            )
        return current_user

    return checker


# Pre-built role dependencies
require_admin = require_roles(UserRole.ADMIN)
require_doctor = require_roles(UserRole.DOCTOR, UserRole.ADMIN)
require_staff = require_roles(UserRole.STAFF, UserRole.ADMIN)
require_patient = require_roles(UserRole.PATIENT)
require_medical = require_roles(UserRole.DOCTOR, UserRole.STAFF, UserRole.ADMIN)


# ==========================================
# PERMISSION-BASED DEPENDENCIES
# ==========================================


def require_permission(permission: Permission):
    """
    Dependency factory for permission-based access.

    Usage:
        @router.post("/prescriptions")
        async def create_prescription(
            current_user: User = Depends(require_permission(Permission.PRESCRIPTION_CREATE))
        ):
            ...
    """
    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        perm_checker = PermissionChecker(current_user)
        if not perm_checker.has_permission(permission):
            raise PermissionDeniedError(permission=permission.value)
        return current_user

    return checker


def require_any_permission(*permissions: Permission):
    """Dependency factory to require any of the specified permissions."""
    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        perm_checker = PermissionChecker(current_user)
        if not perm_checker.has_any_permission(*permissions):
            raise PermissionDeniedError(
                message=f"Required any of: {[p.value for p in permissions]}"
            )
        return current_user

    return checker


def require_all_permissions(*permissions: Permission):
    """Dependency factory to require all of the specified permissions."""
    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        perm_checker = PermissionChecker(current_user)
        if not perm_checker.has_all_permissions(*permissions):
            raise PermissionDeniedError(
                message=f"Required all of: {[p.value for p in permissions]}"
            )
        return current_user

    return checker


# ==========================================
# DEPARTMENT-BASED DEPENDENCIES
# ==========================================


def require_department(*departments: StaffDepartment):
    """
    Dependency factory for department-based access.

    Usage:
        @router.post("/dispense")
        async def dispense_medicine(
            current_user: User = Depends(require_department(StaffDepartment.PHARMACY))
        ):
            ...
    """
    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        # Admin always passes
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Must be staff
        if current_user.role != UserRole.STAFF:
            raise AuthorizationError(message="Staff access required")

        # Check department
        if not current_user.staff_profile:
            raise AuthorizationError(message="Staff profile not found")

        user_dept = current_user.staff_profile.department
        if user_dept not in departments:
            raise AuthorizationError(
                message=f"Access denied. Required departments: {[d.value for d in departments]}"
            )

        return current_user

    return checker


# Pre-built department dependencies
require_pharmacy = require_department(StaffDepartment.PHARMACY)
require_laboratory = require_department(StaffDepartment.LABORATORY)
require_billing = require_department(StaffDepartment.BILLING)
require_nursing = require_department(StaffDepartment.NURSING)
require_reception = require_department(StaffDepartment.RECEPTION)
require_records = require_department(StaffDepartment.RECORDS)
require_it = require_department(StaffDepartment.IT)
require_housekeeping = require_department(StaffDepartment.HOUSEKEEPING)
require_radiology = require_department(StaffDepartment.RADIOLOGY)


# ==========================================
# UTILITY DEPENDENCIES
# ==========================================


async def get_request_info(request: Request) -> dict:
    """Get request information for audit logging."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request.headers.get("x-request-id"),
        "path": str(request.url.path),
        "method": request.method,
    }


class Pagination:
    """Pagination parameters dependency."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100,
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), max_page_size)
        self.offset = (self.page - 1) * self.page_size

    @property
    def skip(self) -> int:
        """Alias for offset."""
        return self.offset

    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size
