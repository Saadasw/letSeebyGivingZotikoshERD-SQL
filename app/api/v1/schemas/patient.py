"""Patient schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.db.models.enums import BloodGroup, Gender
from .base import (
    BaseSchema,
    IDTimestampSchema,
    AddressSchema,
    ContactSchema,
    EmergencyContactSchema,
)


# ==========================================
# PATIENT BASE
# ==========================================


class PatientBase(BaseSchema):
    """Base patient schema."""

    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[BloodGroup] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    insurance_provider: Optional[str] = Field(None, max_length=255)
    insurance_policy_number: Optional[str] = Field(None, max_length=100)
    insurance_expiry: Optional[date] = None
    notes: Optional[str] = None


class PatientAddressContact(AddressSchema, ContactSchema, EmergencyContactSchema):
    """Patient address and contact info."""

    pass


class PatientCreate(PatientBase, PatientAddressContact):
    """Create patient profile schema."""

    user_id: UUID


class PatientUpdate(BaseSchema):
    """Update patient profile schema."""

    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[BloodGroup] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    insurance_provider: Optional[str] = Field(None, max_length=255)
    insurance_policy_number: Optional[str] = Field(None, max_length=100)
    insurance_expiry: Optional[date] = None
    notes: Optional[str] = None
    # Address
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    # Contact
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    # Emergency contact
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_relation: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class PatientResponse(IDTimestampSchema, PatientBase, PatientAddressContact):
    """Patient response schema."""

    user_id: UUID
    patient_id: str  # Auto-generated ID like PAT-001
    first_name: str  # From user
    last_name: str  # From user
    user_email: Optional[str] = None  # From user

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> Optional[int]:
        """Calculate age from date of birth."""
        if self.date_of_birth:
            today = date.today()
            return (
                today.year
                - self.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (self.date_of_birth.month, self.date_of_birth.day)
                )
            )
        return None


class PatientListResponse(BaseSchema):
    """Patient list item (minimal)."""

    id: UUID
    user_id: UUID
    patient_id: str
    first_name: str
    last_name: str
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    is_active: bool = True


class PatientDetailResponse(PatientResponse):
    """Detailed patient response with stats."""

    total_appointments: int = 0
    total_admissions: int = 0
    pending_bills: int = 0
    last_visit: Optional[datetime] = None


# ==========================================
# PATIENT FILTERS
# ==========================================


class PatientFilterParams(BaseSchema):
    """Patient filter parameters."""

    search: Optional[str] = Field(None, description="Search in name, email, or patient_id")
    gender: Optional[Gender] = None
    blood_group: Optional[BloodGroup] = None
    has_insurance: Optional[bool] = None
    min_age: Optional[int] = Field(None, ge=0)
    max_age: Optional[int] = Field(None, ge=0)
    city: Optional[str] = None


# ==========================================
# PATIENT MEDICAL SUMMARY
# ==========================================


class PatientMedicalSummary(BaseSchema):
    """Patient medical summary."""

    patient_id: UUID
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    blood_group: Optional[BloodGroup] = None
    recent_diagnoses: list[str] = []
    active_prescriptions: int = 0
    pending_lab_tests: int = 0


class PatientInsuranceInfo(BaseSchema):
    """Patient insurance information."""

    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    is_valid: bool = False


class PatientEmergencyInfo(BaseSchema):
    """Patient emergency information."""

    patient_id: UUID
    patient_name: str
    blood_group: Optional[BloodGroup] = None
    allergies: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
