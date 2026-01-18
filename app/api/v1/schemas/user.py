"""User schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.db.models.enums import UserRole, StaffDepartment
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# USER BASE
# ==========================================


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    """Create user schema."""

    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole
    department: Optional[StaffDepartment] = None
    branch_id: Optional[UUID] = None
    is_active: bool = True
    is_verified: bool = False


class UserUpdate(BaseSchema):
    """Update user schema."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    department: Optional[StaffDepartment] = None
    branch_id: Optional[UUID] = None


class UserResponse(IDTimestampSchema):
    """User response schema."""

    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    department: Optional[StaffDepartment] = None
    branch_id: Optional[UUID] = None
    last_login: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"


class UserListResponse(BaseSchema):
    """User list item response (minimal)."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    department: Optional[StaffDepartment] = None


class UserDetailResponse(UserResponse):
    """Detailed user response with profile info."""

    profile_id: Optional[UUID] = None
    profile_type: Optional[str] = None


# ==========================================
# USER FILTERS
# ==========================================


class UserFilterParams(BaseSchema):
    """User filter parameters."""

    search: Optional[str] = Field(None, description="Search in name or email")
    role: Optional[UserRole] = None
    department: Optional[StaffDepartment] = None
    branch_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


# ==========================================
# PROFILE IMAGE
# ==========================================


class ProfileImageResponse(BaseSchema):
    """Profile image response."""

    id: UUID
    user_id: UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    is_active: bool
    uploaded_at: datetime


class ProfileImageUploadResponse(BaseSchema):
    """Profile image upload response."""

    message: str = "Image uploaded successfully"
    image: ProfileImageResponse


# ==========================================
# ADMIN USER MANAGEMENT
# ==========================================


class AdminCreateUserRequest(UserCreate):
    """Admin create user request with additional options."""

    send_welcome_email: bool = True
    require_password_change: bool = False


class AdminUpdateUserRequest(UserUpdate):
    """Admin update user request."""

    force_logout: bool = False


class BulkUserStatusUpdate(BaseSchema):
    """Bulk user status update."""

    user_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    is_active: bool


class UserStatsResponse(BaseSchema):
    """User statistics response."""

    total_users: int
    active_users: int
    inactive_users: int
    verified_users: int
    unverified_users: int
    users_by_role: dict[str, int]
    users_by_department: dict[str, int]
    recent_registrations: int
    recent_logins: int
