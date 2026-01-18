"""Staff profile model."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import StaffDepartment

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.branch import Branch
    from app.db.models.inventory import DispenseLog
    from app.db.models.lab_test import LabTest, LabTestSample
    from app.db.models.billing import Payment


class StaffProfile(Base, UUIDMixin, TimestampMixin):
    """Staff profile with department information."""

    __tablename__ = "staff_profile"

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
    department: Mapped[StaffDepartment] = mapped_column(
        ENUM(StaffDepartment, name="staff_department", create_type=False),
        nullable=False,
        default=StaffDepartment.GENERAL,
    )
    employee_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    join_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    shift: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supervisor_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="staff_profile")
    branch: Mapped[Optional["Branch"]] = relationship("Branch", back_populates="staff")
    supervisor: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile", remote_side="StaffProfile.id", back_populates="subordinates"
    )
    subordinates: Mapped[list["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="supervisor"
    )
    dispense_logs: Mapped[list["DispenseLog"]] = relationship(
        "DispenseLog", back_populates="dispensed_by_staff"
    )
    lab_tests_as_technician: Mapped[list["LabTest"]] = relationship(
        "LabTest", back_populates="technician", foreign_keys="LabTest.technician_id"
    )
    samples_collected: Mapped[list["LabTestSample"]] = relationship(
        "LabTestSample", back_populates="collected_by_staff", foreign_keys="LabTestSample.collected_by"
    )
    payments_processed: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="processed_by_staff", foreign_keys="Payment.processed_by"
    )

    @property
    def full_name(self) -> str:
        """Get staff's full name from user."""
        return self.user.name if self.user else ""

    @property
    def is_reception(self) -> bool:
        return self.department == StaffDepartment.RECEPTION

    @property
    def is_laboratory(self) -> bool:
        return self.department == StaffDepartment.LABORATORY

    @property
    def is_pharmacy(self) -> bool:
        return self.department == StaffDepartment.PHARMACY

    @property
    def is_billing(self) -> bool:
        return self.department == StaffDepartment.BILLING

    @property
    def is_nursing(self) -> bool:
        return self.department == StaffDepartment.NURSING

    def __repr__(self) -> str:
        return f"<StaffProfile {self.employee_id} ({self.department.value})>"
