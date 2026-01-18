"""Prescription schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import PrescriptionStatus
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# PRESCRIPTION ITEM
# ==========================================


class PrescriptionItemBase(BaseSchema):
    """Base prescription item schema."""

    medicine_id: UUID
    dosage: str = Field(..., max_length=100)
    frequency: str = Field(..., max_length=100)
    duration: str = Field(..., max_length=100)
    quantity: int = Field(..., ge=1)
    instructions: Optional[str] = Field(None, max_length=500)
    is_as_needed: bool = False


class PrescriptionItemCreate(PrescriptionItemBase):
    """Create prescription item schema."""

    pass


class PrescriptionItemUpdate(BaseSchema):
    """Update prescription item schema."""

    dosage: Optional[str] = Field(None, max_length=100)
    frequency: Optional[str] = Field(None, max_length=100)
    duration: Optional[str] = Field(None, max_length=100)
    quantity: Optional[int] = Field(None, ge=1)
    instructions: Optional[str] = Field(None, max_length=500)
    is_as_needed: Optional[bool] = None


class PrescriptionItemResponse(IDTimestampSchema, PrescriptionItemBase):
    """Prescription item response schema."""

    prescription_id: UUID
    dispensed_quantity: int
    is_dispensed: bool
    # Joined fields
    medicine_name: Optional[str] = None
    medicine_generic_name: Optional[str] = None
    medicine_strength: Optional[str] = None


# ==========================================
# PRESCRIPTION
# ==========================================


class PrescriptionBase(BaseSchema):
    """Base prescription schema."""

    notes: Optional[str] = None
    valid_until: Optional[date] = None


class PrescriptionCreate(PrescriptionBase):
    """Create prescription schema."""

    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    medical_record_id: Optional[UUID] = None
    items: list[PrescriptionItemCreate] = Field(..., min_length=1)


class PrescriptionUpdate(BaseSchema):
    """Update prescription schema."""

    notes: Optional[str] = None
    valid_until: Optional[date] = None
    status: Optional[PrescriptionStatus] = None


class PrescriptionResponse(IDTimestampSchema, PrescriptionBase):
    """Prescription response schema."""

    prescription_id: str  # Auto-generated RX-001
    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    medical_record_id: Optional[UUID] = None
    status: PrescriptionStatus
    # Joined fields
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None


class PrescriptionListResponse(BaseSchema):
    """Prescription list item."""

    id: UUID
    prescription_id: str
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    status: PrescriptionStatus
    item_count: int
    valid_until: Optional[date] = None
    created_at: datetime


class PrescriptionDetailResponse(PrescriptionResponse):
    """Detailed prescription response."""

    items: list[PrescriptionItemResponse] = []
    total_items: int = 0
    dispensed_items: int = 0


# ==========================================
# PRESCRIPTION FILTERS
# ==========================================


class PrescriptionFilterParams(BaseSchema):
    """Prescription filter parameters."""

    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    status: Optional[PrescriptionStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    is_expired: Optional[bool] = None


# ==========================================
# DISPENSE
# ==========================================


class DispenseItemRequest(BaseSchema):
    """Dispense item request."""

    prescription_item_id: UUID
    quantity: int = Field(..., ge=1)
    batch_number: Optional[str] = None
    notes: Optional[str] = None


class DispenseRequest(BaseSchema):
    """Dispense prescription request."""

    items: list[DispenseItemRequest] = Field(..., min_length=1)
    dispensed_by: Optional[UUID] = None
    notes: Optional[str] = None


class DispenseResponse(BaseSchema):
    """Dispense response."""

    prescription_id: UUID
    dispensed_items: list[DispenseItemRequest]
    dispensed_by: Optional[UUID] = None
    dispensed_at: datetime
    message: str = "Items dispensed successfully"
