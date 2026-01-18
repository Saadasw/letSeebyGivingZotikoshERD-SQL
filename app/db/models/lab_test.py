"""Lab Test related models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import (
    LabPriority,
    LabTestStatus,
    SampleType,
    StorageCondition,
    SampleStatus,
)

if TYPE_CHECKING:
    from app.db.models.patient import PatientProfile
    from app.db.models.doctor import DoctorProfile
    from app.db.models.branch import Branch
    from app.db.models.medical_record import MedicalRecord
    from app.db.models.staff import StaffProfile
    from app.db.models.user import User


class LabTestType(Base, UUIDMixin, TimestampMixin):
    """Lab test type catalog."""

    __tablename__ = "lab_test_type"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    turnaround_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sample_type: Mapped[Optional[SampleType]] = mapped_column(
        ENUM(SampleType, name="sample_type", create_type=False),
        nullable=True,
    )
    sample_volume: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    container_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collection_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fasting_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fasting_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    home_collection_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    report_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normal_range: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    lab_tests: Mapped[list["LabTest"]] = relationship(
        "LabTest", back_populates="test_type"
    )

    def __repr__(self) -> str:
        return f"<LabTestType {self.code}: {self.name}>"


class LabTest(Base, UUIDMixin, TimestampMixin):
    """Individual lab test order."""

    __tablename__ = "lab_test"

    test_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patient_profile.id", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctor_profile.id", ondelete="RESTRICT"),
        nullable=False,
    )
    test_type_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lab_test_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    medical_record_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medical_record.id", ondelete="SET NULL"),
        nullable=True,
    )
    priority: Mapped[LabPriority] = mapped_column(
        ENUM(LabPriority, name="lab_priority", create_type=False),
        nullable=False,
        default=LabPriority.ROUTINE,
    )
    status: Mapped[LabTestStatus] = mapped_column(
        ENUM(LabTestStatus, name="lab_test_status", create_type=False),
        nullable=False,
        default=LabTestStatus.ORDERED,
    )
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clinical_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result_flag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reference_range: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technician_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    technician_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    report_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    sample_collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="lab_tests"
    )
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="lab_tests", foreign_keys=[doctor_id]
    )
    test_type: Mapped["LabTestType"] = relationship(
        "LabTestType", back_populates="lab_tests"
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="lab_tests")
    medical_record: Mapped[Optional["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="lab_tests"
    )
    technician: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="lab_tests_as_technician", foreign_keys=[technician_id]
    )
    samples: Mapped[list["LabTestSample"]] = relationship(
        "LabTestSample", back_populates="lab_test", cascade="all, delete-orphan"
    )

    @property
    def is_completed(self) -> bool:
        """Check if test is completed."""
        return self.status == LabTestStatus.COMPLETED

    @property
    def is_urgent(self) -> bool:
        """Check if test is urgent."""
        return self.priority in [LabPriority.URGENT, LabPriority.STAT]

    def __repr__(self) -> str:
        return f"<LabTest {self.test_no} ({self.status.value})>"


class LabTestSample(Base, UUIDMixin, TimestampMixin):
    """Lab test sample tracking."""

    __tablename__ = "lab_test_sample"

    sample_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    lab_test_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lab_test.id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_type: Mapped[SampleType] = mapped_column(
        ENUM(SampleType, name="sample_type", create_type=False),
        nullable=False,
    )
    collection_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collected_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    collection_site: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    storage_condition: Mapped[Optional[StorageCondition]] = mapped_column(
        ENUM(StorageCondition, name="storage_condition", create_type=False),
        nullable=True,
    )
    container_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    volume_ml: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[SampleStatus] = mapped_column(
        ENUM(SampleStatus, name="sample_status", create_type=False),
        nullable=False,
        default=SampleStatus.COLLECTED,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rejection_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disposed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    disposed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disposal_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lab_test: Mapped["LabTest"] = relationship(
        "LabTest", back_populates="samples"
    )
    collected_by_staff: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="samples_collected", foreign_keys=[collected_by]
    )

    @property
    def is_rejected(self) -> bool:
        """Check if sample is rejected."""
        return self.status == SampleStatus.REJECTED

    def __repr__(self) -> str:
        return f"<LabTestSample {self.sample_no} ({self.status.value})>"
