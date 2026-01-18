"""Billing schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import BillStatus, PaymentMethod, PaymentStatus
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# BILL ITEM
# ==========================================


class BillItemBase(BaseSchema):
    """Base bill item schema."""

    description: str = Field(..., max_length=500)
    item_type: str = Field(..., max_length=100)
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    tax_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    notes: Optional[str] = None


class BillItemCreate(BillItemBase):
    """Create bill item schema."""

    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = Field(None, max_length=50)


class BillItemUpdate(BaseSchema):
    """Update bill item schema."""

    description: Optional[str] = Field(None, max_length=500)
    quantity: Optional[int] = Field(None, ge=1)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class BillItemResponse(IDTimestampSchema, BillItemBase):
    """Bill item response schema."""

    bill_id: UUID
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal


# ==========================================
# BILL
# ==========================================


class BillBase(BaseSchema):
    """Base bill schema."""

    notes: Optional[str] = None
    due_date: Optional[date] = None


class BillCreate(BillBase):
    """Create bill schema."""

    patient_id: UUID
    branch_id: UUID
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    items: list[BillItemCreate] = Field(default_factory=list)


class BillUpdate(BaseSchema):
    """Update bill schema."""

    notes: Optional[str] = None
    due_date: Optional[date] = None
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)


class BillStatusUpdate(BaseSchema):
    """Update bill status schema."""

    status: BillStatus
    reason: Optional[str] = None


class BillResponse(IDTimestampSchema, BillBase):
    """Bill response schema."""

    bill_number: str  # Auto-generated BILL-001
    patient_id: UUID
    branch_id: UUID
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    status: BillStatus
    subtotal: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    generated_by: Optional[UUID] = None
    # Joined fields
    patient_name: Optional[str] = None
    branch_name: Optional[str] = None


class BillListResponse(BaseSchema):
    """Bill list item."""

    id: UUID
    bill_number: str
    patient_id: UUID
    patient_name: str
    branch_id: UUID
    status: BillStatus
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    due_date: Optional[date] = None
    created_at: datetime


class BillDetailResponse(BillResponse):
    """Detailed bill response."""

    items: list[BillItemResponse] = []
    payments: list["PaymentResponse"] = []
    generated_by_name: Optional[str] = None


# ==========================================
# PAYMENT
# ==========================================


class PaymentBase(BaseSchema):
    """Base payment schema."""

    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Create payment schema."""

    bill_id: UUID


class PaymentResponse(IDTimestampSchema, PaymentBase):
    """Payment response schema."""

    payment_id: str  # Auto-generated PAY-001
    bill_id: UUID
    status: PaymentStatus
    payment_date: datetime
    processed_by: Optional[UUID] = None
    # Joined fields
    bill_number: Optional[str] = None
    patient_name: Optional[str] = None
    processed_by_name: Optional[str] = None


class PaymentListResponse(BaseSchema):
    """Payment list item."""

    id: UUID
    payment_id: str
    bill_id: UUID
    bill_number: str
    patient_name: str
    amount: Decimal
    payment_method: PaymentMethod
    status: PaymentStatus
    payment_date: datetime


# ==========================================
# REFUND
# ==========================================


class RefundRequest(BaseSchema):
    """Refund request schema."""

    payment_id: UUID
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=500)
    refund_method: Optional[PaymentMethod] = None


class RefundResponse(BaseSchema):
    """Refund response schema."""

    payment_id: UUID
    refund_amount: Decimal
    reason: str
    refunded_at: datetime
    refunded_by: Optional[UUID] = None


# ==========================================
# BILLING FILTERS
# ==========================================


class BillFilterParams(BaseSchema):
    """Bill filter parameters."""

    patient_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    status: Optional[BillStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    is_overdue: Optional[bool] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    search: Optional[str] = Field(None, description="Search in bill number or patient")


class PaymentFilterParams(BaseSchema):
    """Payment filter parameters."""

    bill_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    payment_method: Optional[PaymentMethod] = None
    status: Optional[PaymentStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


# ==========================================
# BILLING STATISTICS
# ==========================================


class BillingStatsResponse(BaseSchema):
    """Billing statistics response."""

    total_bills: int
    pending_bills: int
    paid_bills: int
    partially_paid_bills: int
    overdue_bills: int
    total_billed: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    collection_rate: float = 0.0
    by_branch: dict[str, Decimal]
    by_payment_method: dict[str, Decimal]


class DailyRevenueReport(BaseSchema):
    """Daily revenue report."""

    date: date
    total_billed: Decimal
    total_collected: Decimal
    new_bills: int
    payments_received: int


class PatientBillingSummary(BaseSchema):
    """Patient billing summary."""

    patient_id: UUID
    patient_name: str
    total_billed: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    overdue_amount: Decimal
    last_payment_date: Optional[datetime] = None


# Forward references
BillDetailResponse.model_rebuild()
