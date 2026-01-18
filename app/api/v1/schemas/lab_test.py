"""Lab test schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import LabTestStatus, SampleStatus
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# LAB TEST TYPE
# ==========================================


class LabTestTypeBase(BaseSchema):
    """Base lab test type schema."""

    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    category: str = Field(..., max_length=100)
    description: Optional[str] = None
    sample_type: str = Field(..., max_length=100)
    sample_volume: Optional[str] = Field(None, max_length=50)
    turnaround_time: Optional[str] = Field(None, max_length=50)
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    normal_range: Optional[str] = None
    preparation_instructions: Optional[str] = None


class LabTestTypeCreate(LabTestTypeBase):
    """Create lab test type schema."""

    pass


class LabTestTypeUpdate(BaseSchema):
    """Update lab test type schema."""

    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    sample_type: Optional[str] = Field(None, max_length=100)
    sample_volume: Optional[str] = Field(None, max_length=50)
    turnaround_time: Optional[str] = Field(None, max_length=50)
    price: Optional[Decimal] = Field(None, ge=0)
    normal_range: Optional[str] = None
    preparation_instructions: Optional[str] = None
    is_active: Optional[bool] = None


class LabTestTypeResponse(IDTimestampSchema, LabTestTypeBase):
    """Lab test type response schema."""

    is_active: bool


class LabTestTypeListResponse(BaseSchema):
    """Lab test type list item."""

    id: UUID
    name: str
    code: str
    category: str
    sample_type: str
    price: Decimal
    is_active: bool


# ==========================================
# LAB TEST
# ==========================================


class LabTestBase(BaseSchema):
    """Base lab test schema."""

    priority: str = Field("normal", pattern="^(normal|urgent|stat)$")
    clinical_notes: Optional[str] = None


class LabTestCreate(LabTestBase):
    """Create lab test schema."""

    patient_id: UUID
    doctor_id: UUID
    test_type_id: UUID
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None


class LabTestUpdate(BaseSchema):
    """Update lab test schema."""

    priority: Optional[str] = Field(None, pattern="^(normal|urgent|stat)$")
    clinical_notes: Optional[str] = None


class LabTestResultUpdate(BaseSchema):
    """Update lab test results schema."""

    results: str
    result_values: Optional[dict] = None
    is_abnormal: bool = False
    technician_notes: Optional[str] = None


class LabTestResponse(IDTimestampSchema, LabTestBase):
    """Lab test response schema."""

    test_id: str  # Auto-generated LAB-001
    patient_id: UUID
    doctor_id: UUID
    test_type_id: UUID
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    status: LabTestStatus
    ordered_at: datetime
    collected_at: Optional[datetime] = None
    results_at: Optional[datetime] = None
    results: Optional[str] = None
    result_values: Optional[dict] = None
    is_abnormal: bool
    technician_notes: Optional[str] = None
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    # Joined fields
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    test_type_name: Optional[str] = None
    test_type_category: Optional[str] = None


class LabTestListResponse(BaseSchema):
    """Lab test list item."""

    id: UUID
    test_id: str
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    test_type_name: str
    status: LabTestStatus
    priority: str
    is_abnormal: bool
    ordered_at: datetime


class LabTestDetailResponse(LabTestResponse):
    """Detailed lab test response."""

    samples: list["LabTestSampleResponse"] = []
    test_type: Optional[LabTestTypeResponse] = None
    verified_by_name: Optional[str] = None


# ==========================================
# LAB TEST SAMPLE
# ==========================================


class LabTestSampleBase(BaseSchema):
    """Base lab test sample schema."""

    sample_number: str = Field(..., max_length=50)
    sample_type: str = Field(..., max_length=100)
    volume: Optional[str] = Field(None, max_length=50)
    collection_notes: Optional[str] = None


class LabTestSampleCreate(LabTestSampleBase):
    """Create lab test sample schema."""

    lab_test_id: UUID
    collected_by: Optional[UUID] = None


class LabTestSampleUpdate(BaseSchema):
    """Update lab test sample schema."""

    status: Optional[SampleStatus] = None
    storage_location: Optional[str] = Field(None, max_length=100)
    processing_notes: Optional[str] = None


class LabTestSampleResponse(IDTimestampSchema, LabTestSampleBase):
    """Lab test sample response schema."""

    lab_test_id: UUID
    status: SampleStatus
    collected_by: Optional[UUID] = None
    collected_at: datetime
    processed_at: Optional[datetime] = None
    storage_location: Optional[str] = None
    processing_notes: Optional[str] = None
    # Joined fields
    collected_by_name: Optional[str] = None


# ==========================================
# LAB TEST FILTERS
# ==========================================


class LabTestFilterParams(BaseSchema):
    """Lab test filter parameters."""

    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    test_type_id: Optional[UUID] = None
    status: Optional[LabTestStatus] = None
    priority: Optional[str] = Field(None, pattern="^(normal|urgent|stat)$")
    is_abnormal: Optional[bool] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    search: Optional[str] = Field(None, description="Search in test name or patient")


class LabTestTypeFilterParams(BaseSchema):
    """Lab test type filter parameters."""

    search: Optional[str] = Field(None, description="Search in name or code")
    category: Optional[str] = None
    sample_type: Optional[str] = None
    is_active: Optional[bool] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None


# ==========================================
# LAB TEST STATISTICS
# ==========================================


class LabTestStatsResponse(BaseSchema):
    """Lab test statistics response."""

    total_tests: int
    pending: int
    in_progress: int
    completed: int
    abnormal_results: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    average_turnaround_hours: Optional[float] = None


# Forward references
LabTestDetailResponse.model_rebuild()
