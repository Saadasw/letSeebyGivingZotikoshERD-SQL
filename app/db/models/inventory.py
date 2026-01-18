"""Inventory and Dispense Log models."""

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import InventoryStatus, DispenseLogStatus

if TYPE_CHECKING:
    from app.db.models.medicine import Medicine
    from app.db.models.branch import Branch
    from app.db.models.prescription import PrescriptionItem
    from app.db.models.patient import PatientProfile
    from app.db.models.staff import StaffProfile


class Inventory(Base, UUIDMixin, TimestampMixin):
    """Medicine inventory per branch and batch."""

    __tablename__ = "inventory"

    medicine_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medicine.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manufacturing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rack_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[InventoryStatus] = mapped_column(
        ENUM(InventoryStatus, name="inventory_status", create_type=False),
        nullable=False,
        default=InventoryStatus.IN_STOCK,
    )
    last_restocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_dispensed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_quantity_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_reserved_non_negative"),
        UniqueConstraint("medicine_id", "branch_id", "batch_number", name="uq_inventory"),
    )

    # Relationships
    medicine: Mapped["Medicine"] = relationship("Medicine", back_populates="inventory")
    branch: Mapped["Branch"] = relationship("Branch", back_populates="inventory")
    dispense_logs: Mapped[list["DispenseLog"]] = relationship(
        "DispenseLog", back_populates="inventory"
    )

    @property
    def available_quantity(self) -> int:
        """Get available quantity (excluding reserved)."""
        return self.quantity - self.reserved_quantity

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is low."""
        return self.quantity <= self.reorder_level

    @property
    def is_expired(self) -> bool:
        """Check if batch is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date <= date.today()

    @property
    def days_to_expiry(self) -> Optional[int]:
        """Get days until expiry."""
        if not self.expiry_date:
            return None
        delta = self.expiry_date - date.today()
        return delta.days

    def __repr__(self) -> str:
        return f"<Inventory {self.batch_number} qty={self.quantity}>"


class DispenseLog(Base, UUIDMixin):
    """Log of medicine dispensing."""

    __tablename__ = "dispense_log"

    dispense_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    prescription_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prescription_item.id", ondelete="RESTRICT"),
        nullable=False,
    )
    inventory_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("inventory.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patient_profile.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dispensed_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dispensed_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_refills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[DispenseLogStatus] = mapped_column(
        ENUM(DispenseLogStatus, name="dispense_log_status", create_type=False),
        nullable=False,
        default=DispenseLogStatus.DISPENSED,
    )
    unit_price_at_dispense: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    returned_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    returned_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispensed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint("dispensed_quantity > 0", name="ck_dispense_quantity_positive"),
    )

    # Relationships
    prescription_item: Mapped["PrescriptionItem"] = relationship(
        "PrescriptionItem", back_populates="dispense_logs"
    )
    inventory: Mapped["Inventory"] = relationship(
        "Inventory", back_populates="dispense_logs"
    )
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="dispense_logs"
    )
    dispensed_by_staff: Mapped["StaffProfile"] = relationship(
        "StaffProfile", back_populates="dispense_logs", foreign_keys=[dispensed_by]
    )

    def __repr__(self) -> str:
        return f"<DispenseLog {self.dispense_no} qty={self.dispensed_quantity}>"
