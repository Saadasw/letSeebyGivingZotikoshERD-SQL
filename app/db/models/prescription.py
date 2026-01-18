"""Prescription related models."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import PrescriptionStatus, DispenseStatus

if TYPE_CHECKING:
    from app.db.models.medical_record import MedicalRecord
    from app.db.models.patient import PatientProfile
    from app.db.models.doctor import DoctorProfile
    from app.db.models.branch import Branch
    from app.db.models.medicine import Medicine
    from app.db.models.inventory import DispenseLog


class Prescription(Base, UUIDMixin, TimestampMixin):
    """Prescription issued by doctor."""

    __tablename__ = "prescription"

    prescription_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    medical_record_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medical_record.id", ondelete="RESTRICT"),
        nullable=False,
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
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    diagnosis: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[PrescriptionStatus] = mapped_column(
        ENUM(PrescriptionStatus, name="prescription_status", create_type=False),
        nullable=False,
        default=PrescriptionStatus.ACTIVE,
    )
    valid_from: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pharmacy_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doctor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    medical_record: Mapped["MedicalRecord"] = relationship(
        "MedicalRecord", back_populates="prescriptions"
    )
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="prescriptions"
    )
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="prescriptions", foreign_keys=[doctor_id]
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="prescriptions")
    items: Mapped[list["PrescriptionItem"]] = relationship(
        "PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan"
    )

    @property
    def is_valid(self) -> bool:
        """Check if prescription is still valid."""
        if self.status not in [PrescriptionStatus.ACTIVE, PrescriptionStatus.PARTIALLY_DISPENSED]:
            return False
        if self.valid_until and self.valid_until < date.today():
            return False
        return True

    @property
    def is_fully_dispensed(self) -> bool:
        """Check if all items are dispensed."""
        return self.status == PrescriptionStatus.FULLY_DISPENSED

    def __repr__(self) -> str:
        return f"<Prescription {self.prescription_no} ({self.status.value})>"


class PrescriptionItem(Base, UUIDMixin, TimestampMixin):
    """Individual medicine in a prescription."""

    __tablename__ = "prescription_item"

    prescription_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prescription.id", ondelete="CASCADE"),
        nullable=False,
    )
    medicine_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medicine.id", ondelete="RESTRICT"),
        nullable=False,
    )
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dosage_form: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    frequency_times: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    route: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timing: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meal_relation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    refills_allowed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refills_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispense_status: Mapped[DispenseStatus] = mapped_column(
        ENUM(DispenseStatus, name="dispense_status", create_type=False),
        nullable=False,
        default=DispenseStatus.PENDING,
    )
    dispensed_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quantity_positive"),
        CheckConstraint("refills_remaining <= refills_allowed", name="ck_refills_valid"),
    )

    # Relationships
    prescription: Mapped["Prescription"] = relationship(
        "Prescription", back_populates="items"
    )
    medicine: Mapped["Medicine"] = relationship(
        "Medicine", back_populates="prescription_items"
    )
    dispense_logs: Mapped[list["DispenseLog"]] = relationship(
        "DispenseLog", back_populates="prescription_item"
    )

    @property
    def remaining_quantity(self) -> int:
        """Get remaining quantity to dispense."""
        return self.quantity - self.dispensed_quantity

    @property
    def is_fully_dispensed(self) -> bool:
        """Check if item is fully dispensed."""
        return self.dispense_status == DispenseStatus.COMPLETE

    def __repr__(self) -> str:
        return f"<PrescriptionItem {self.medicine_name} x{self.quantity}>"
