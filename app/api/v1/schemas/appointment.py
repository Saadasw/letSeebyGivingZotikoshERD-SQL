"""Appointment schemas."""

from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import AppointmentStatus, AppointmentType
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# TIME SLOT
# ==========================================


class TimeSlotBase(BaseSchema):
    """Base time slot schema."""

    doctor_id: UUID
    branch_id: UUID
    slot_date: date
    start_time: time
    end_time: time
    max_bookings: int = Field(1, ge=1, le=10)


class TimeSlotCreate(TimeSlotBase):
    """Create time slot schema."""

    pass


class TimeSlotResponse(IDTimestampSchema, TimeSlotBase):
    """Time slot response schema."""

    current_bookings: int
    is_available: bool

    @property
    def available_spots(self) -> int:
        """Get available spots."""
        return max(0, self.max_bookings - self.current_bookings)


class TimeSlotListResponse(BaseSchema):
    """Time slot list item."""

    id: UUID
    slot_date: date
    start_time: time
    end_time: time
    is_available: bool
    available_spots: int


# ==========================================
# APPOINTMENT
# ==========================================


class AppointmentBase(BaseSchema):
    """Base appointment schema."""

    appointment_type: AppointmentType = AppointmentType.CONSULTATION
    reason: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Create appointment schema."""

    patient_id: UUID
    doctor_id: UUID
    branch_id: UUID
    time_slot_id: Optional[UUID] = None
    scheduled_date: date
    scheduled_time: time


class AppointmentUpdate(BaseSchema):
    """Update appointment schema."""

    appointment_type: Optional[AppointmentType] = None
    reason: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = None
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    time_slot_id: Optional[UUID] = None


class AppointmentStatusUpdate(BaseSchema):
    """Update appointment status schema."""

    status: AppointmentStatus
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    doctor_notes: Optional[str] = None


class AppointmentResponse(IDTimestampSchema, AppointmentBase):
    """Appointment response schema."""

    appointment_id: str  # Auto-generated APT-001
    patient_id: UUID
    doctor_id: UUID
    branch_id: UUID
    time_slot_id: Optional[UUID] = None
    status: AppointmentStatus
    scheduled_date: date
    scheduled_time: time
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    consultation_fee: Decimal
    cancellation_reason: Optional[str] = None
    doctor_notes: Optional[str] = None
    # Joined fields
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    branch_name: Optional[str] = None


class AppointmentListResponse(BaseSchema):
    """Appointment list item (minimal)."""

    id: UUID
    appointment_id: str
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    branch_id: UUID
    scheduled_date: date
    scheduled_time: time
    status: AppointmentStatus
    appointment_type: AppointmentType


class AppointmentDetailResponse(AppointmentResponse):
    """Detailed appointment response."""

    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None
    doctor_specialization: Optional[str] = None
    has_medical_record: bool = False
    has_prescription: bool = False
    has_lab_tests: bool = False


# ==========================================
# APPOINTMENT FILTERS
# ==========================================


class AppointmentFilterParams(BaseSchema):
    """Appointment filter parameters."""

    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    status: Optional[AppointmentStatus] = None
    appointment_type: Optional[AppointmentType] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    search: Optional[str] = Field(None, description="Search in patient/doctor name")


# ==========================================
# APPOINTMENT ACTIONS
# ==========================================


class AppointmentCheckInRequest(BaseSchema):
    """Appointment check-in request."""

    notes: Optional[str] = None


class AppointmentCheckOutRequest(BaseSchema):
    """Appointment check-out request."""

    doctor_notes: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[date] = None


class RescheduleAppointmentRequest(BaseSchema):
    """Reschedule appointment request."""

    new_date: date
    new_time: time
    new_time_slot_id: Optional[UUID] = None
    reason: Optional[str] = None


class CancelAppointmentRequest(BaseSchema):
    """Cancel appointment request."""

    reason: str = Field(..., min_length=1, max_length=500)


# ==========================================
# APPOINTMENT STATISTICS
# ==========================================


class AppointmentStatsResponse(BaseSchema):
    """Appointment statistics response."""

    total_appointments: int
    scheduled: int
    confirmed: int
    completed: int
    cancelled: int
    no_show: int
    by_type: dict[str, int]
    by_doctor: dict[str, int]
    by_branch: dict[str, int]


class DoctorAppointmentStats(BaseSchema):
    """Doctor appointment statistics."""

    doctor_id: UUID
    doctor_name: str
    total: int
    completed: int
    cancelled: int
    completion_rate: float


class DailyAppointmentSummary(BaseSchema):
    """Daily appointment summary."""

    date: date
    total: int
    scheduled: int
    completed: int
    cancelled: int
    no_show: int
