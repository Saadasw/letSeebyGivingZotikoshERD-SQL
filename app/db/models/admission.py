"""Admission model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import AdmissionStatus, AdmissionType

if TYPE_CHECKING:
    from app.db.models.patient import PatientProfile
    from app.db.models.doctor import DoctorProfile
    from app.db.models.room import Room, Bed
    from app.db.models.branch import Branch
    from app.db.models.billing import Bill


class Admission(Base, UUIDMixin, TimestampMixin):
    """Patient admission record."""

    __tablename__ = "admission"

    admission_no: Mapped[str] = mapped_column(
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
    room_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("room.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bed_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bed.id", ondelete="SET NULL"),
        nullable=True,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    admission_type: Mapped[AdmissionType] = mapped_column(
        ENUM(AdmissionType, name="admission_type", create_type=False),
        nullable=False,
        default=AdmissionType.ELECTIVE,
    )
    admission_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expected_discharge_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_discharge_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[AdmissionStatus] = mapped_column(
        ENUM(AdmissionStatus, name="admission_status", create_type=False),
        nullable=False,
        default=AdmissionStatus.ADMITTED,
    )
    admission_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admission_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attending_doctor_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctor_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    referred_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    referral_hospital: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    discharge_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discharge_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discharge_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discharge_medications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    discharged_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    transfer_to_room_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("room.id", ondelete="SET NULL"),
        nullable=True,
    )
    transfer_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transferred_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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
        "PatientProfile", back_populates="admissions"
    )
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="admissions", foreign_keys=[doctor_id]
    )
    attending_doctor: Mapped[Optional["DoctorProfile"]] = relationship(
        "DoctorProfile", foreign_keys=[attending_doctor_id]
    )
    room: Mapped["Room"] = relationship(
        "Room", back_populates="admissions", foreign_keys=[room_id]
    )
    bed: Mapped[Optional["Bed"]] = relationship(
        "Bed", back_populates="admissions", foreign_keys=[bed_id]
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="admissions")
    transfer_to_room: Mapped[Optional["Room"]] = relationship(
        "Room", back_populates="transfer_admissions", foreign_keys=[transfer_to_room_id]
    )
    bills: Mapped[list["Bill"]] = relationship(
        "Bill", back_populates="admission"
    )

    @property
    def is_active(self) -> bool:
        """Check if admission is active."""
        return self.status == AdmissionStatus.ADMITTED

    @property
    def is_discharged(self) -> bool:
        """Check if patient is discharged."""
        return self.status == AdmissionStatus.DISCHARGED

    @property
    def length_of_stay(self) -> Optional[int]:
        """Calculate length of stay in days."""
        end_date = self.actual_discharge_date or datetime.utcnow()
        delta = end_date - self.admission_date
        return delta.days

    def __repr__(self) -> str:
        return f"<Admission {self.admission_no} ({self.status.value})>"
