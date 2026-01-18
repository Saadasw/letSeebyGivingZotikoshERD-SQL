"""Branch model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.doctor import DoctorProfile, DoctorBranchAssignment, DoctorWeeklySchedule
    from app.db.models.staff import StaffProfile
    from app.db.models.appointment import TimeSlot, Appointment
    from app.db.models.medical_record import MedicalRecord
    from app.db.models.prescription import Prescription
    from app.db.models.inventory import Inventory
    from app.db.models.lab_test import LabTest
    from app.db.models.room import Room
    from app.db.models.admission import Admission
    from app.db.models.billing import Bill


class Branch(Base, UUIDMixin, TimestampMixin):
    """Hospital branch/location model."""

    __tablename__ = "branch"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Bangladesh", nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_main_branch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    doctors: Mapped[list["DoctorProfile"]] = relationship(
        "DoctorProfile", back_populates="branch"
    )
    doctor_assignments: Mapped[list["DoctorBranchAssignment"]] = relationship(
        "DoctorBranchAssignment", back_populates="branch", cascade="all, delete-orphan"
    )
    staff: Mapped[list["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="branch"
    )
    schedules: Mapped[list["DoctorWeeklySchedule"]] = relationship(
        "DoctorWeeklySchedule", back_populates="branch", cascade="all, delete-orphan"
    )
    time_slots: Mapped[list["TimeSlot"]] = relationship(
        "TimeSlot", back_populates="branch", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="branch"
    )
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="branch"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="branch"
    )
    inventory: Mapped[list["Inventory"]] = relationship(
        "Inventory", back_populates="branch", cascade="all, delete-orphan"
    )
    lab_tests: Mapped[list["LabTest"]] = relationship(
        "LabTest", back_populates="branch"
    )
    rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="branch", cascade="all, delete-orphan"
    )
    admissions: Mapped[list["Admission"]] = relationship(
        "Admission", back_populates="branch"
    )
    bills: Mapped[list["Bill"]] = relationship(
        "Bill", back_populates="branch"
    )

    @property
    def full_address(self) -> str:
        """Get full formatted address."""
        parts = [self.address, self.city, self.state, self.postal_code, self.country]
        return ", ".join(filter(None, parts))

    def __repr__(self) -> str:
        return f"<Branch {self.code}: {self.name}>"
