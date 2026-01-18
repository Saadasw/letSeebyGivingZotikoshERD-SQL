"""Authentication schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.db.models.enums import UserRole, StaffDepartment
from .base import BaseSchema


# ==========================================
# LOGIN / TOKEN
# ==========================================


class LoginRequest(BaseSchema):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseSchema):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""

    refresh_token: str


class TokenPayload(BaseSchema):
    """Token payload schema."""

    sub: str
    exp: datetime
    iat: datetime
    type: str
    role: Optional[str] = None
    department: Optional[str] = None


# ==========================================
# REGISTRATION
# ==========================================


class RegisterRequest(BaseSchema):
    """User registration request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class PatientRegisterRequest(RegisterRequest):
    """Patient registration request schema."""

    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None


# ==========================================
# PASSWORD MANAGEMENT
# ==========================================


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseSchema):
    """Forgot password request schema."""

    email: EmailStr


class ResetPasswordRequest(BaseSchema):
    """Reset password request schema."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


# ==========================================
# SESSION
# ==========================================


class SessionInfo(BaseSchema):
    """User session information."""

    session_id: UUID
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    last_activity: datetime
    created_at: datetime
    is_current: bool = False


class ActiveSessionsResponse(BaseSchema):
    """Active sessions response."""

    sessions: list[SessionInfo]
    total: int


class RevokeSessionRequest(BaseSchema):
    """Revoke session request."""

    session_id: UUID


# ==========================================
# CURRENT USER
# ==========================================


class CurrentUserResponse(BaseSchema):
    """Current authenticated user response."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    department: Optional[StaffDepartment] = None
    branch_id: Optional[UUID] = None
    profile_id: Optional[UUID] = None
    last_login: Optional[datetime] = None
    created_at: datetime


class VerifyEmailRequest(BaseSchema):
    """Email verification request."""

    token: str


class ResendVerificationRequest(BaseSchema):
    """Resend verification email request."""

    email: EmailStr
