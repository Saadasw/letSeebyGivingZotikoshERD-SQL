"""Medical Record related models."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import MedicalRecordStatus

if TYPE_CHECKING:
    from app.db.models.patient import PatientProfile
    from app.db.models.doctor import DoctorProfile
    from app.db.models.branch import Branch
    from app.db.models.appointment import Appointment
    from app.db.models.user import User
    from app.db.models.prescription import Prescription
    from app.db.models.lab_test import LabTest


class MedicalRecord(Base, UUIDMixin, TimestampMixin):
    """Patient medical record created during visit."""

    __tablename__ = "medical_record"

    record_no: Mapped[str] = mapped_column(
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
    appointment_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointment.id", ondelete="SET NULL"),
        nullable=True,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    history_of_present_illness: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    past_medical_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    examination_findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    differential_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[MedicalRecordStatus] = mapped_column(
        ENUM(MedicalRecordStatus, name="medical_record_status", create_type=False),
        nullable=False,
        default=MedicalRecordStatus.DRAFT,
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalized_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="medical_records"
    )
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="medical_records", foreign_keys=[doctor_id]
    )
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment", back_populates="medical_records"
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="medical_records")
    history: Mapped[list["MedicalRecordHistory"]] = relationship(
        "MedicalRecordHistory", back_populates="medical_record", cascade="all, delete-orphan"
    )
    vitals: Mapped[list["Vitals"]] = relationship(
        "Vitals", back_populates="medical_record", cascade="all, delete-orphan"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="medical_record"
    )
    lab_tests: Mapped[list["LabTest"]] = relationship(
        "LabTest", back_populates="medical_record"
    )

    @property
    def is_finalized(self) -> bool:
        """Check if record is finalized."""
        return self.status == MedicalRecordStatus.FINALIZED

    @property
    def can_edit(self) -> bool:
        """Check if record can be edited."""
        return self.status == MedicalRecordStatus.DRAFT

    def __repr__(self) -> str:
        return f"<MedicalRecord {self.record_no} ({self.status.value})>"


class MedicalRecordHistory(Base, UUIDMixin):
    """Version history for medical records (for amendments)."""

    __tablename__ = "medical_record_history"

    medical_record_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medical_record.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    history_of_present_illness: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    examination_findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[MedicalRecordStatus]] = mapped_column(
        ENUM(MedicalRecordStatus, name="medical_record_status", create_type=False),
        nullable=True,
    )
    modified_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    modification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    medical_record: Mapped["MedicalRecord"] = relationship(
        "MedicalRecord", back_populates="history"
    )

    def __repr__(self) -> str:
        return f"<MedicalRecordHistory v{self.version}>"


class Vitals(Base, UUIDMixin, TimestampMixin):
    """Patient vital signs."""

    __tablename__ = "vitals"

    medical_record_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medical_record.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patient_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    recorded_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    temperature_unit: Mapped[str] = mapped_column(String(1), default="C", nullable=True)
    blood_pressure_systolic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blood_pressure_diastolic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pulse_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(2), default="kg", nullable=True)
    height: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    height_unit: Mapped[str] = mapped_column(String(2), default="cm", nullable=True)
    bmi: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    oxygen_saturation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blood_glucose: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 1), nullable=True)
    blood_glucose_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pain_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "temperature IS NULL OR temperature BETWEEN 30 AND 45",
            name="ck_temperature_range"
        ),
        CheckConstraint(
            "blood_pressure_systolic IS NULL OR blood_pressure_systolic BETWEEN 50 AND 300",
            name="ck_bp_systolic_range"
        ),
        CheckConstraint(
            "blood_pressure_diastolic IS NULL OR blood_pressure_diastolic BETWEEN 30 AND 200",
            name="ck_bp_diastolic_range"
        ),
        CheckConstraint(
            "pulse_rate IS NULL OR pulse_rate BETWEEN 20 AND 250",
            name="ck_pulse_range"
        ),
        CheckConstraint(
            "oxygen_saturation IS NULL OR oxygen_saturation BETWEEN 0 AND 100",
            name="ck_spo2_range"
        ),
        CheckConstraint(
            "pain_level IS NULL OR pain_level BETWEEN 0 AND 10",
            name="ck_pain_level_range"
        ),
    )

    # Relationships
    medical_record: Mapped["MedicalRecord"] = relationship(
        "MedicalRecord", back_populates="vitals"
    )
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="vitals"
    )

    @property
    def blood_pressure(self) -> Optional[str]:
        """Get formatted blood pressure."""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None

    def __repr__(self) -> str:
        return f"<Vitals {self.recorded_at}>"
