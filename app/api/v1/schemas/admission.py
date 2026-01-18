"""Admission schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import AdmissionStatus
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# ADMISSION
# ==========================================


class AdmissionBase(BaseSchema):
    """Base admission schema."""

    admission_reason: str = Field(..., max_length=1000)
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    notes: Optional[str] = None
    expected_discharge_date: Optional[date] = None


class AdmissionCreate(AdmissionBase):
    """Create admission schema."""

    patient_id: UUID
    doctor_id: UUID
    branch_id: UUID
    bed_id: UUID
    admission_date: Optional[datetime] = None


class AdmissionUpdate(BaseSchema):
    """Update admission schema."""

    admission_reason: Optional[str] = Field(None, max_length=1000)
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    notes: Optional[str] = None
    expected_discharge_date: Optional[date] = None
    attending_doctor_id: Optional[UUID] = None


class AdmissionStatusUpdate(BaseSchema):
    """Update admission status schema."""

    status: AdmissionStatus
    discharge_notes: Optional[str] = None
    discharge_instructions: Optional[str] = None


class AdmissionResponse(IDTimestampSchema, AdmissionBase):
    """Admission response schema."""

    admission_id: str  # Auto-generated ADM-001
    patient_id: UUID
    doctor_id: UUID
    branch_id: UUID
    bed_id: UUID
    status: AdmissionStatus
    admission_date: datetime
    discharge_date: Optional[datetime] = None
    discharge_notes: Optional[str] = None
    discharge_instructions: Optional[str] = None
    total_days: int = 0
    total_charges: Decimal = Decimal("0.00")
    # Joined fields
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    branch_name: Optional[str] = None
    room_number: Optional[str] = None
    bed_number: Optional[str] = None


class AdmissionListResponse(BaseSchema):
    """Admission list item."""

    id: UUID
    admission_id: str
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    branch_id: UUID
    bed_id: UUID
    room_number: str
    bed_number: str
    status: AdmissionStatus
    admission_date: datetime
    expected_discharge_date: Optional[date] = None


class AdmissionDetailResponse(AdmissionResponse):
    """Detailed admission response."""

    medical_records: list = []
    lab_tests: list = []
    prescriptions: list = []
    bills: list = []
    vitals_history: list = []


# ==========================================
# ADMISSION ACTIONS
# ==========================================


class DischargeRequest(BaseSchema):
    """Discharge patient request."""

    discharge_notes: Optional[str] = None
    discharge_instructions: Optional[str] = None
    follow_up_date: Optional[date] = None
    prescriptions_on_discharge: Optional[list[UUID]] = None


class TransferAdmissionRequest(BaseSchema):
    """Transfer admission to different bed/room."""

    new_bed_id: UUID
    reason: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = None


class ExtendStayRequest(BaseSchema):
    """Extend expected discharge date."""

    new_expected_discharge_date: date
    reason: str = Field(..., min_length=1, max_length=500)


# ==========================================
# ADMISSION FILTERS
# ==========================================


class AdmissionFilterParams(BaseSchema):
    """Admission filter parameters."""

    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    bed_id: Optional[UUID] = None
    status: Optional[AdmissionStatus] = None
    admission_date_from: Optional[date] = None
    admission_date_to: Optional[date] = None
    search: Optional[str] = Field(None, description="Search in patient name")


# ==========================================
# ADMISSION STATISTICS
# ==========================================


class AdmissionStatsResponse(BaseSchema):
    """Admission statistics response."""

    total_admissions: int
    active_admissions: int
    discharged_today: int
    expected_discharges_today: int
    average_stay_days: float = 0.0
    by_branch: dict[str, int]
    by_status: dict[str, int]


class DailyAdmissionSummary(BaseSchema):
    """Daily admission summary."""

    date: date
    new_admissions: int
    discharges: int
    current_occupancy: int
    expected_discharges: int
