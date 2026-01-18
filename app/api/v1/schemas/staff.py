"""Staff schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import StaffDepartment
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# STAFF PROFILE
# ==========================================


class StaffProfileBase(BaseSchema):
    """Base staff profile schema."""

    department: StaffDepartment
    position: str = Field(..., max_length=100)
    employee_id: Optional[str] = Field(None, max_length=50)
    hire_date: Optional[date] = None
    qualifications: Optional[str] = None
    certifications: Optional[str] = None


class StaffProfileCreate(StaffProfileBase):
    """Create staff profile schema."""

    user_id: UUID
    branch_id: UUID


class StaffProfileUpdate(BaseSchema):
    """Update staff profile schema."""

    department: Optional[StaffDepartment] = None
    position: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=50)
    hire_date: Optional[date] = None
    qualifications: Optional[str] = None
    certifications: Optional[str] = None
    branch_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class StaffProfileResponse(IDTimestampSchema, StaffProfileBase):
    """Staff profile response schema."""

    user_id: UUID
    staff_id: str  # Auto-generated STF-001
    branch_id: UUID
    is_active: bool
    first_name: str  # From user
    last_name: str  # From user
    email: Optional[str] = None
    phone: Optional[str] = None
    branch_name: Optional[str] = None  # From branch

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"


class StaffListResponse(BaseSchema):
    """Staff list item (minimal)."""

    id: UUID
    user_id: UUID
    staff_id: str
    first_name: str
    last_name: str
    department: StaffDepartment
    position: str
    branch_id: UUID
    branch_name: Optional[str] = None
    is_active: bool


class StaffDetailResponse(StaffProfileResponse):
    """Detailed staff response."""

    user_is_active: bool = True
    user_is_verified: bool = False
    last_login: Optional[datetime] = None


# ==========================================
# STAFF FILTERS
# ==========================================


class StaffFilterParams(BaseSchema):
    """Staff filter parameters."""

    search: Optional[str] = Field(None, description="Search in name or employee_id")
    department: Optional[StaffDepartment] = None
    branch_id: Optional[UUID] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None
    hired_after: Optional[date] = None
    hired_before: Optional[date] = None


# ==========================================
# STAFF STATISTICS
# ==========================================


class StaffStatsResponse(BaseSchema):
    """Staff statistics response."""

    total_staff: int
    active_staff: int
    by_department: dict[str, int]
    by_branch: dict[str, int]
    recent_hires: int
