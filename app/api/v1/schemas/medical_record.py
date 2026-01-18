"""Medical record schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, IDTimestampSchema


# ==========================================
# VITALS
# ==========================================


class VitalsBase(BaseSchema):
    """Base vitals schema."""

    temperature: Optional[Decimal] = Field(None, description="Temperature in Celsius")
    blood_pressure_systolic: Optional[int] = Field(None, ge=0, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=0, le=200)
    pulse_rate: Optional[int] = Field(None, ge=0, le=300)
    respiratory_rate: Optional[int] = Field(None, ge=0, le=100)
    oxygen_saturation: Optional[Decimal] = Field(None, ge=0, le=100)
    weight: Optional[Decimal] = Field(None, ge=0, description="Weight in kg")
    height: Optional[Decimal] = Field(None, ge=0, description="Height in cm")
    notes: Optional[str] = None


class VitalsCreate(VitalsBase):
    """Create vitals schema."""

    patient_id: UUID
    recorded_by: Optional[UUID] = None


class VitalsUpdate(VitalsBase):
    """Update vitals schema."""

    pass


class VitalsResponse(IDTimestampSchema, VitalsBase):
    """Vitals response schema."""

    patient_id: UUID
    recorded_by: Optional[UUID] = None
    recorded_by_name: Optional[str] = None

    @property
    def blood_pressure(self) -> Optional[str]:
        """Get formatted blood pressure."""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None

    @property
    def bmi(self) -> Optional[Decimal]:
        """Calculate BMI."""
        if self.weight and self.height and self.height > 0:
            height_m = self.height / Decimal("100")
            return round(self.weight / (height_m * height_m), 2)
        return None


# ==========================================
# MEDICAL RECORD
# ==========================================


class MedicalRecordBase(BaseSchema):
    """Base medical record schema."""

    chief_complaint: str = Field(..., max_length=500)
    present_illness: Optional[str] = None
    past_medical_history: Optional[str] = None
    family_history: Optional[str] = None
    social_history: Optional[str] = None
    physical_examination: Optional[str] = None
    diagnosis: Optional[str] = None
    differential_diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    follow_up_date: Optional[date] = None
    is_confidential: bool = False


class MedicalRecordCreate(MedicalRecordBase):
    """Create medical record schema."""

    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None


class MedicalRecordUpdate(BaseSchema):
    """Update medical record schema."""

    chief_complaint: Optional[str] = Field(None, max_length=500)
    present_illness: Optional[str] = None
    past_medical_history: Optional[str] = None
    family_history: Optional[str] = None
    social_history: Optional[str] = None
    physical_examination: Optional[str] = None
    diagnosis: Optional[str] = None
    differential_diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    follow_up_date: Optional[date] = None
    is_confidential: Optional[bool] = None


class MedicalRecordResponse(IDTimestampSchema, MedicalRecordBase):
    """Medical record response schema."""

    record_id: str  # Auto-generated MR-001
    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    version: int
    # Joined fields
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None


class MedicalRecordListResponse(BaseSchema):
    """Medical record list item."""

    id: UUID
    record_id: str
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    chief_complaint: str
    diagnosis: Optional[str] = None
    is_confidential: bool
    created_at: datetime


class MedicalRecordDetailResponse(MedicalRecordResponse):
    """Detailed medical record response."""

    vitals: Optional[VitalsResponse] = None
    prescriptions: list = []
    lab_tests: list = []
    history: list["MedicalRecordHistoryResponse"] = []


# ==========================================
# MEDICAL RECORD HISTORY
# ==========================================


class MedicalRecordHistoryResponse(BaseSchema):
    """Medical record history response."""

    id: UUID
    medical_record_id: UUID
    version: int
    changed_by: UUID
    changed_by_name: Optional[str] = None
    changes: dict
    created_at: datetime


# ==========================================
# MEDICAL RECORD FILTERS
# ==========================================


class MedicalRecordFilterParams(BaseSchema):
    """Medical record filter parameters."""

    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    search: Optional[str] = Field(None, description="Search in diagnosis or complaint")
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    is_confidential: Optional[bool] = None


# Forward references
MedicalRecordDetailResponse.model_rebuild()
