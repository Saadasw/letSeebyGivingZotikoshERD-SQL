"""Patient profile model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import GenderType

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.appointment import Appointment
    from app.db.models.medical_record import MedicalRecord, Vitals
    from app.db.models.prescription import Prescription
    from app.db.models.inventory import DispenseLog
    from app.db.models.lab_test import LabTest
    from app.db.models.room import Bed
    from app.db.models.admission import Admission
    from app.db.models.billing import Bill


class PatientProfile(Base, UUIDMixin, TimestampMixin):
    """Patient profile with medical history."""

    __tablename__ = "patient_profile"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    patient_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[GenderType]] = mapped_column(
        ENUM(GenderType, name="gender_type", create_type=False),
        nullable=True,
    )
    blood_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emergency_contact_relation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chronic_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_medications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    family_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(50), default="bn", nullable=True)
    consent_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    consent_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="patient_profile")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="patient"
    )
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="patient"
    )
    vitals: Mapped[list["Vitals"]] = relationship(
        "Vitals", back_populates="patient", cascade="all, delete-orphan"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="patient"
    )
    dispense_logs: Mapped[list["DispenseLog"]] = relationship(
        "DispenseLog", back_populates="patient"
    )
    lab_tests: Mapped[list["LabTest"]] = relationship(
        "LabTest", back_populates="patient"
    )
    current_bed: Mapped[Optional["Bed"]] = relationship(
        "Bed", back_populates="current_patient", foreign_keys="Bed.current_patient_id"
    )
    admissions: Mapped[list["Admission"]] = relationship(
        "Admission", back_populates="patient"
    )
    bills: Mapped[list["Bill"]] = relationship(
        "Bill", back_populates="patient"
    )

    @property
    def full_name(self) -> str:
        """Get patient's full name from user."""
        return self.user.name if self.user else ""

    @property
    def age(self) -> Optional[int]:
        """Calculate patient's age."""
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def has_allergies(self) -> bool:
        """Check if patient has any allergies."""
        return bool(self.allergies and self.allergies.strip())

    def __repr__(self) -> str:
        return f"<PatientProfile {self.patient_id}>"
