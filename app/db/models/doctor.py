"""Doctor related models."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import ScheduleOverrideType

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.branch import Branch
    from app.db.models.appointment import TimeSlot, Appointment
    from app.db.models.medical_record import MedicalRecord
    from app.db.models.prescription import Prescription
    from app.db.models.lab_test import LabTest
    from app.db.models.admission import Admission


class DoctorProfile(Base, UUIDMixin, TimestampMixin):
    """Doctor profile with medical credentials."""

    __tablename__ = "doctor_profile"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    branch_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="SET NULL"),
        nullable=True,
    )
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    license_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    license_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    follow_up_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    slot_duration: Mapped[int] = mapped_column(Integer, default=30, nullable=True)
    max_patients_per_day: Mapped[int] = mapped_column(Integer, default=30, nullable=True)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("slot_duration >= 5 AND slot_duration <= 120", name="ck_slot_duration"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    branch: Mapped[Optional["Branch"]] = relationship("Branch", back_populates="doctors")
    branch_assignments: Mapped[list["DoctorBranchAssignment"]] = relationship(
        "DoctorBranchAssignment", back_populates="doctor", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["DoctorWeeklySchedule"]] = relationship(
        "DoctorWeeklySchedule", back_populates="doctor", cascade="all, delete-orphan"
    )
    schedule_overrides: Mapped[list["DoctorScheduleOverride"]] = relationship(
        "DoctorScheduleOverride", back_populates="doctor", cascade="all, delete-orphan"
    )
    time_slots: Mapped[list["TimeSlot"]] = relationship(
        "TimeSlot", back_populates="doctor", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id"
    )
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="doctor", foreign_keys="MedicalRecord.doctor_id"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="doctor", foreign_keys="Prescription.doctor_id"
    )
    lab_tests: Mapped[list["LabTest"]] = relationship(
        "LabTest", back_populates="doctor", foreign_keys="LabTest.doctor_id"
    )
    admissions: Mapped[list["Admission"]] = relationship(
        "Admission", back_populates="doctor", foreign_keys="Admission.doctor_id"
    )

    @property
    def full_name(self) -> str:
        """Get doctor's full name from user."""
        return self.user.name if self.user else ""

    @property
    def is_license_valid(self) -> bool:
        """Check if license is still valid."""
        if not self.license_expiry:
            return True
        return self.license_expiry >= date.today()

    def __repr__(self) -> str:
        return f"<DoctorProfile {self.license_number}>"


class DoctorBranchAssignment(Base, UUIDMixin, TimestampMixin):
    """Doctor assignment to branches (many-to-many)."""

    __tablename__ = "doctor_branch_assignment"

    doctor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctor_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_primary_branch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consultation_room: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("doctor_id", "branch_id", name="uq_doctor_branch"),)

    # Relationships
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="branch_assignments"
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="doctor_assignments")

    def __repr__(self) -> str:
        return f"<DoctorBranchAssignment doctor={self.doctor_id} branch={self.branch_id}>"


class DoctorWeeklySchedule(Base, UUIDMixin, TimestampMixin):
    """Doctor's recurring weekly schedule."""

    __tablename__ = "doctor_weekly_schedule"

    doctor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctor_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Sunday, 6=Saturday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    break_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    max_appointments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_day_of_week"),
        CheckConstraint("end_time > start_time", name="ck_schedule_times"),
        UniqueConstraint("doctor_id", "branch_id", "day_of_week", name="uq_doctor_branch_day"),
    )

    # Relationships
    doctor: Mapped["DoctorProfile"] = relationship("DoctorProfile", back_populates="schedules")
    branch: Mapped["Branch"] = relationship("Branch", back_populates="schedules")
    time_slots: Mapped[list["TimeSlot"]] = relationship(
        "TimeSlot", back_populates="schedule", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        return f"<Schedule {days[self.day_of_week]} {self.start_time}-{self.end_time}>"


class DoctorScheduleOverride(Base, UUIDMixin, TimestampMixin):
    """Override for doctor's schedule (leave, extra hours, etc.)."""

    __tablename__ = "doctor_schedule_override"

    doctor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctor_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="SET NULL"),
        nullable=True,
    )
    override_date: Mapped[date] = mapped_column(Date, nullable=False)
    override_type: Mapped[ScheduleOverrideType] = mapped_column(
        ENUM(ScheduleOverrideType, name="schedule_override_type", create_type=False),
        nullable=False,
    )
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_full_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="schedule_overrides"
    )

    def __repr__(self) -> str:
        return f"<ScheduleOverride {self.override_date} ({self.override_type.value})>"
