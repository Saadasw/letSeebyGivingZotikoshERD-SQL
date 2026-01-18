"""Billing and Payment models."""

from datetime import date, datetime
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
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import (
    PaymentStatus,
    PaymentMethod,
    PaymentTransactionStatus,
    BillItemType,
)

if TYPE_CHECKING:
    from app.db.models.patient import PatientProfile
    from app.db.models.branch import Branch
    from app.db.models.appointment import Appointment
    from app.db.models.admission import Admission
    from app.db.models.user import User
    from app.db.models.staff import StaffProfile


class Bill(Base, UUIDMixin, TimestampMixin):
    """Patient bill."""

    __tablename__ = "bill"

    bill_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patient_profile.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    appointment_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointment.id", ondelete="SET NULL"),
        nullable=True,
    )
    admission_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admission.id", ondelete="SET NULL"),
        nullable=True,
    )
    bill_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    discount_approved_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    due_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        ENUM(PaymentStatus, name="payment_status", create_type=False),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_subtotal_non_negative"),
        CheckConstraint("tax_amount >= 0", name="ck_tax_non_negative"),
        CheckConstraint("discount_amount >= 0", name="ck_discount_non_negative"),
        CheckConstraint("total_amount >= 0", name="ck_total_non_negative"),
        CheckConstraint("paid_amount >= 0", name="ck_paid_non_negative"),
        CheckConstraint("due_amount >= 0", name="ck_due_non_negative"),
    )

    # Relationships
    patient: Mapped["PatientProfile"] = relationship(
        "PatientProfile", back_populates="bills"
    )
    branch: Mapped["Branch"] = relationship("Branch", back_populates="bills")
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment", back_populates="bills"
    )
    admission: Mapped[Optional["Admission"]] = relationship(
        "Admission", back_populates="bills"
    )
    items: Mapped[list["BillItem"]] = relationship(
        "BillItem", back_populates="bill", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="bill"
    )

    @property
    def is_paid(self) -> bool:
        """Check if bill is fully paid."""
        return self.payment_status == PaymentStatus.PAID

    @property
    def is_overdue(self) -> bool:
        """Check if bill is overdue."""
        if self.payment_status == PaymentStatus.PAID:
            return False
        if self.due_date and self.due_date < date.today():
            return True
        return False

    def __repr__(self) -> str:
        return f"<Bill {self.bill_no} ({self.payment_status.value})>"


class BillItem(Base, UUIDMixin, TimestampMixin):
    """Individual item in a bill."""

    __tablename__ = "bill_item"

    bill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bill.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[BillItemType] = mapped_column(
        ENUM(BillItemType, name="bill_item_type", create_type=False),
        nullable=False,
    )
    reference_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    service_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_item_price_non_negative"),
    )

    # Relationships
    bill: Mapped["Bill"] = relationship("Bill", back_populates="items")

    def __repr__(self) -> str:
        return f"<BillItem {self.description[:30]}>"


class Payment(Base, UUIDMixin):
    """Payment transaction for a bill."""

    __tablename__ = "payment"

    bill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bill.id", ondelete="RESTRICT"),
        nullable=False,
    )
    receipt_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        ENUM(PaymentMethod, name="payment_method", create_type=False),
        nullable=False,
    )
    transaction_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    card_last_four: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    mobile_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[PaymentTransactionStatus] = mapped_column(
        ENUM(PaymentTransactionStatus, name="payment_transaction_status", create_type=False),
        nullable=False,
        default=PaymentTransactionStatus.PENDING,
    )
    payment_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    processed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refund_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_payment_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payment.id", ondelete="SET NULL"),
        nullable=True,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
    )

    # Relationships
    bill: Mapped["Bill"] = relationship("Bill", back_populates="payments")
    processed_by_staff: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="payments_processed", foreign_keys=[processed_by]
    )
    original_payment: Mapped[Optional["Payment"]] = relationship(
        "Payment", remote_side="Payment.id", back_populates="refund_payments"
    )
    refund_payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="original_payment"
    )

    @property
    def is_completed(self) -> bool:
        """Check if payment is completed."""
        return self.status == PaymentTransactionStatus.COMPLETED

    def __repr__(self) -> str:
        return f"<Payment {self.receipt_no} ({self.status.value})>"
