"""Appointment and TimeSlot models."""

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
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
from app.db.models.enums import TimeSlotStatus, AppointmentType, AppointmentStatus

if TYPE_CHECKING:
    from app.db.models.doctor import DoctorProfile, DoctorWeeklySchedule
    from app.db.models.patient import PatientProfile
    from app.db.models.branch import Branch
    from app.db.models.user import User
    from app.db.models.medical_record import MedicalRecord
    from app.db.models.billing import Bill


class TimeSlot(Base, UUIDMixin, TimestampMixin):
    """Generated time slots for appointments."""

    __tablename__ = "time_slot"

    schedule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctor_weekly_schedule.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[TimeSlotStatus] = mapped_column(
        ENUM(TimeSlotStatus, name="time_slot_status", create_type=False),
        nullable=False,
        default=TimeSlotStatus.AVAILABLE,
    )
    blocked_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    appointment_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_slot_times"),
        UniqueConstraint(
            "doctor_id", "branch_id", "slot_date", "start_time", name="uq_slot"
        ),
    )

    # Relationships
    schedule: Mapped["DoctorWeeklySchedule"] = relationship(
        "DoctorWeeklySchedule", back_populates="time_slots"
    )
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="time_slots"
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="time_slots")
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment", back_populates="time_slot", foreign_keys="Appointment.time_slot_id"
    )

    @property
    def is_available(self) -> bool:
        """Check if slot is available for booking."""
        return self.status == TimeSlotStatus.AVAILABLE

    @property
    def is_past(self) -> bool:
        """Check if slot is in the past."""
        now = datetime.now()
        slot_datetime = datetime.combine(self.slot_date, self.start_time)
        return slot_datetime < now

    def __repr__(self) -> str:
        return f"<TimeSlot {self.slot_date} {self.start_time}-{self.end_time}>"


class Appointment(Base, UUIDMixin, TimestampMixin):
    """Patient appointment with doctor."""

    __tablename__ = "appointment"

    appointment_no: Mapped[str] = mapped_column(
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
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    time_slot_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("time_slot.id", ondelete="SET NULL"),
        nullable=True,
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    appointment_type: Mapped[AppointmentType] = mapped_column(
        ENUM(AppointmentType, name="appointment_type", create_type=False),
        nullable=False,
        default=AppointmentType.CONSULTATION,
    )
    visit_type: Mapped[str] = mapped_column(String(50), default="in_person", nullable=True)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        ENUM(AppointmentStatus, name="appointment_status", create_type=False),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
    )
    queue_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="appointments"
    )
    doctor: Mapped["DoctorProfile"] = relationship(
        "DoctorProfile", back_populates="appointments", foreign_keys=[doctor_id]
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="appointments")
    time_slot: Mapped[Optional["TimeSlot"]] = relationship(
        "TimeSlot", back_populates="appointment", foreign_keys=[time_slot_id]
    )
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="appointment"
    )
    bills: Mapped[list["Bill"]] = relationship(
        "Bill", back_populates="appointment"
    )

    @property
    def is_upcoming(self) -> bool:
        """Check if appointment is in the future."""
        now = datetime.now()
        appt_datetime = datetime.combine(self.appointment_date, self.start_time)
        return appt_datetime > now

    @property
    def can_cancel(self) -> bool:
        """Check if appointment can be cancelled."""
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]

    @property
    def can_check_in(self) -> bool:
        """Check if patient can check in."""
        return self.status == AppointmentStatus.CONFIRMED

    def __repr__(self) -> str:
        return f"<Appointment {self.appointment_no} ({self.status.value})>"
