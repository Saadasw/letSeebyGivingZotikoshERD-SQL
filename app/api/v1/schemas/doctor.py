"""Doctor schemas."""

from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import DayOfWeek, Gender, Specialization
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# DOCTOR PROFILE
# ==========================================


class DoctorProfileBase(BaseSchema):
    """Base doctor profile schema."""

    specialization: Specialization
    qualification: str = Field(..., max_length=500)
    experience_years: int = Field(0, ge=0)
    license_number: str = Field(..., max_length=100)
    license_expiry: Optional[date] = None
    consultation_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    bio: Optional[str] = None


class DoctorProfileCreate(DoctorProfileBase):
    """Create doctor profile schema."""

    user_id: UUID


class DoctorProfileUpdate(BaseSchema):
    """Update doctor profile schema."""

    specialization: Optional[Specialization] = None
    qualification: Optional[str] = Field(None, max_length=500)
    experience_years: Optional[int] = Field(None, ge=0)
    license_number: Optional[str] = Field(None, max_length=100)
    license_expiry: Optional[date] = None
    consultation_fee: Optional[Decimal] = Field(None, ge=0)
    bio: Optional[str] = None
    is_available: Optional[bool] = None


class DoctorProfileResponse(IDTimestampSchema, DoctorProfileBase):
    """Doctor profile response schema."""

    user_id: UUID
    doctor_id: str  # Auto-generated DOC-001
    is_available: bool
    first_name: str  # From user
    last_name: str  # From user
    email: Optional[str] = None
    phone: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Get full name with title."""
        return f"Dr. {self.first_name} {self.last_name}"


class DoctorListResponse(BaseSchema):
    """Doctor list item (minimal)."""

    id: UUID
    user_id: UUID
    doctor_id: str
    first_name: str
    last_name: str
    specialization: Specialization
    consultation_fee: Decimal
    is_available: bool
    experience_years: int


class DoctorDetailResponse(DoctorProfileResponse):
    """Detailed doctor response."""

    branches: list["BranchAssignmentResponse"] = []
    total_patients: int = 0
    total_appointments: int = 0
    average_rating: Optional[Decimal] = None


# ==========================================
# DOCTOR BRANCH ASSIGNMENT
# ==========================================


class BranchAssignmentBase(BaseSchema):
    """Base branch assignment schema."""

    branch_id: UUID
    is_primary: bool = False


class BranchAssignmentCreate(BranchAssignmentBase):
    """Create branch assignment schema."""

    doctor_id: UUID


class BranchAssignmentResponse(BaseSchema):
    """Branch assignment response."""

    id: UUID
    branch_id: UUID
    branch_name: str
    is_primary: bool
    assigned_at: datetime


# ==========================================
# DOCTOR SCHEDULE
# ==========================================


class WeeklyScheduleBase(BaseSchema):
    """Base weekly schedule schema."""

    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(30, ge=5, le=120)
    max_patients_per_slot: int = Field(1, ge=1, le=10)


class WeeklyScheduleCreate(WeeklyScheduleBase):
    """Create weekly schedule schema."""

    doctor_id: UUID
    branch_id: UUID


class WeeklyScheduleUpdate(BaseSchema):
    """Update weekly schedule schema."""

    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_duration_minutes: Optional[int] = Field(None, ge=5, le=120)
    max_patients_per_slot: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


class WeeklyScheduleResponse(IDTimestampSchema, WeeklyScheduleBase):
    """Weekly schedule response."""

    doctor_id: UUID
    branch_id: UUID
    is_active: bool


# ==========================================
# SCHEDULE OVERRIDE
# ==========================================


class ScheduleOverrideBase(BaseSchema):
    """Base schedule override schema."""

    override_date: date
    is_available: bool = False
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = Field(None, max_length=500)


class ScheduleOverrideCreate(ScheduleOverrideBase):
    """Create schedule override schema."""

    doctor_id: UUID
    branch_id: Optional[UUID] = None


class ScheduleOverrideResponse(IDTimestampSchema, ScheduleOverrideBase):
    """Schedule override response."""

    doctor_id: UUID
    branch_id: Optional[UUID] = None


# ==========================================
# DOCTOR FILTERS & AVAILABILITY
# ==========================================


class DoctorFilterParams(BaseSchema):
    """Doctor filter parameters."""

    search: Optional[str] = Field(None, description="Search in name")
    specialization: Optional[Specialization] = None
    branch_id: Optional[UUID] = None
    is_available: Optional[bool] = None
    min_experience: Optional[int] = Field(None, ge=0)
    max_fee: Optional[Decimal] = Field(None, ge=0)


class DoctorAvailabilityRequest(BaseSchema):
    """Doctor availability request."""

    doctor_id: UUID
    branch_id: UUID
    date: date


class TimeSlotInfo(BaseSchema):
    """Time slot information."""

    start_time: time
    end_time: time
    is_available: bool
    booked_count: int = 0
    max_capacity: int = 1


class DoctorAvailabilityResponse(BaseSchema):
    """Doctor availability response."""

    doctor_id: UUID
    branch_id: UUID
    date: date
    is_working: bool
    slots: list[TimeSlotInfo] = []
    override_reason: Optional[str] = None


# Forward references
DoctorDetailResponse.model_rebuild()
