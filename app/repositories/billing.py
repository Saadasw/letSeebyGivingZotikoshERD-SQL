"""Billing repository."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.enums import BillStatus, PaymentMethod, PaymentStatus
from app.db.models.billing import Bill, BillItem, Payment
from app.db.models.patient import PatientProfile
from app.db.models.user import User
from .base import BaseRepository


class BillRepository(BaseRepository[Bill]):
    """Repository for Bill model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Bill, db)

    async def get_by_bill_number(self, bill_number: str) -> Optional[Bill]:
        """Get bill by auto-generated number."""
        query = select(Bill).where(Bill.bill_number == bill_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[Bill]:
        """Get bill with items and payments."""
        query = (
            select(Bill)
            .where(Bill.id == id)
            .options(
                joinedload(Bill.patient).joinedload(PatientProfile.user),
                joinedload(Bill.branch),
                selectinload(Bill.items),
                selectinload(Bill.payments),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_bills_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        appointment_id: Optional[UUID] = None,
        admission_id: Optional[UUID] = None,
        status: Optional[BillStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        is_overdue: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Sequence[Bill]:
        """Get list of bills with filters."""
        query = (
            select(Bill)
            .options(
                joinedload(Bill.patient).joinedload(PatientProfile.user),
                joinedload(Bill.branch),
            )
        )

        conditions = []

        if patient_id:
            conditions.append(Bill.patient_id == patient_id)
        if branch_id:
            conditions.append(Bill.branch_id == branch_id)
        if appointment_id:
            conditions.append(Bill.appointment_id == appointment_id)
        if admission_id:
            conditions.append(Bill.admission_id == admission_id)
        if status:
            conditions.append(Bill.status == status)
        if date_from:
            conditions.append(func.date(Bill.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(Bill.created_at) <= date_to)

        today = date.today()
        if is_overdue is not None:
            if is_overdue:
                conditions.append(
                    and_(
                        Bill.due_date.isnot(None),
                        Bill.due_date < today,
                        Bill.status.in_([BillStatus.PENDING, BillStatus.PARTIALLY_PAID]),
                    )
                )
            else:
                conditions.append(
                    or_(
                        Bill.due_date.is_(None),
                        Bill.due_date >= today,
                        Bill.status.in_([BillStatus.PAID, BillStatus.CANCELLED]),
                    )
                )

        if search:
            query = query.join(
                PatientProfile, Bill.patient_id == PatientProfile.id
            ).join(
                User, PatientProfile.user_id == User.id
            )
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    Bill.bill_number.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Bill.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_bills(
        self,
        *,
        patient_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[BillStatus] = None,
    ) -> int:
        """Count bills matching filters."""
        query = select(func.count(Bill.id))

        conditions = []
        if patient_id:
            conditions.append(Bill.patient_id == patient_id)
        if branch_id:
            conditions.append(Bill.branch_id == branch_id)
        if status:
            conditions.append(Bill.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_patient_bills(
        self,
        patient_id: UUID,
        *,
        pending_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Bill]:
        """Get bills for a patient."""
        query = (
            select(Bill)
            .where(Bill.patient_id == patient_id)
            .options(selectinload(Bill.items))
        )

        if pending_only:
            query = query.where(
                Bill.status.in_([BillStatus.PENDING, BillStatus.PARTIALLY_PAID])
            )

        query = query.order_by(Bill.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_with_items(
        self,
        bill_data: dict,
        items_data: list[dict],
    ) -> Bill:
        """Create bill with items and calculate totals."""
        # Calculate totals
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_discount = Decimal("0.00")

        for item in items_data:
            item_subtotal = Decimal(str(item["quantity"])) * item["unit_price"]
            item_discount = item_subtotal * item.get("discount_percent", Decimal("0.00")) / 100
            item_after_discount = item_subtotal - item_discount
            item_tax = item_after_discount * item.get("tax_percent", Decimal("0.00")) / 100

            subtotal += item_subtotal
            total_discount += item_discount
            total_tax += item_tax

        bill_discount = subtotal * bill_data.get("discount_percent", Decimal("0.00")) / 100
        total_amount = subtotal - total_discount - bill_discount + total_tax

        bill_data.update({
            "subtotal": subtotal,
            "discount_amount": total_discount + bill_discount,
            "tax_amount": total_tax,
            "total_amount": total_amount,
            "paid_amount": Decimal("0.00"),
            "balance_amount": total_amount,
        })

        bill = Bill(**bill_data)
        self.db.add(bill)
        await self.db.flush()

        for item_data in items_data:
            item_subtotal = Decimal(str(item_data["quantity"])) * item_data["unit_price"]
            item_discount = item_subtotal * item_data.get("discount_percent", Decimal("0.00")) / 100
            item_after_discount = item_subtotal - item_discount
            item_tax = item_after_discount * item_data.get("tax_percent", Decimal("0.00")) / 100

            item = BillItem(
                bill_id=bill.id,
                subtotal=item_subtotal,
                discount_amount=item_discount,
                tax_amount=item_tax,
                total=item_after_discount + item_tax,
                **item_data,
            )
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(bill)
        return bill

    async def update_amounts(self, bill_id: UUID) -> Optional[Bill]:
        """Recalculate and update bill amounts."""
        bill = await self.get_with_details(bill_id)
        if not bill:
            return None

        subtotal = sum(item.subtotal for item in bill.items)
        total_discount = sum(item.discount_amount for item in bill.items)
        total_tax = sum(item.tax_amount for item in bill.items)

        bill_discount = subtotal * bill.discount_percent / 100
        total_amount = subtotal - total_discount - bill_discount + total_tax

        return await self.update(
            bill_id,
            {
                "subtotal": subtotal,
                "discount_amount": total_discount + bill_discount,
                "tax_amount": total_tax,
                "total_amount": total_amount,
                "balance_amount": total_amount - bill.paid_amount,
            },
        )

    async def add_payment(
        self,
        bill_id: UUID,
        amount: Decimal,
    ) -> Optional[Bill]:
        """Add payment amount to bill."""
        bill = await self.get(bill_id)
        if not bill:
            return None

        new_paid = bill.paid_amount + amount
        new_balance = bill.total_amount - new_paid

        new_status = bill.status
        if new_balance <= 0:
            new_status = BillStatus.PAID
        elif new_paid > 0:
            new_status = BillStatus.PARTIALLY_PAID

        return await self.update(
            bill_id,
            {
                "paid_amount": new_paid,
                "balance_amount": max(Decimal("0.00"), new_balance),
                "status": new_status,
            },
        )


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Payment, db)

    async def get_by_payment_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by auto-generated ID."""
        query = select(Payment).where(Payment.payment_id == payment_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_bill(self, id: UUID) -> Optional[Payment]:
        """Get payment with bill details."""
        query = (
            select(Payment)
            .where(Payment.id == id)
            .options(
                joinedload(Payment.bill).joinedload(Bill.patient).joinedload(PatientProfile.user)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_payments_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        bill_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        payment_method: Optional[PaymentMethod] = None,
        status: Optional[PaymentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Sequence[Payment]:
        """Get list of payments with filters."""
        query = (
            select(Payment)
            .join(Bill)
            .options(
                joinedload(Payment.bill).joinedload(Bill.patient).joinedload(PatientProfile.user)
            )
        )

        conditions = []

        if bill_id:
            conditions.append(Payment.bill_id == bill_id)
        if patient_id:
            conditions.append(Bill.patient_id == patient_id)
        if branch_id:
            conditions.append(Bill.branch_id == branch_id)
        if payment_method:
            conditions.append(Payment.payment_method == payment_method)
        if status:
            conditions.append(Payment.status == status)
        if date_from:
            conditions.append(func.date(Payment.payment_date) >= date_from)
        if date_to:
            conditions.append(func.date(Payment.payment_date) <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Payment.payment_date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def get_bill_payments(self, bill_id: UUID) -> Sequence[Payment]:
        """Get all payments for a bill."""
        query = (
            select(Payment)
            .where(Payment.bill_id == bill_id)
            .order_by(Payment.payment_date.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_billing_stats(
        self,
        branch_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        """Get billing statistics."""
        bill_conditions = []
        if branch_id:
            bill_conditions.append(Bill.branch_id == branch_id)
        if date_from:
            bill_conditions.append(func.date(Bill.created_at) >= date_from)
        if date_to:
            bill_conditions.append(func.date(Bill.created_at) <= date_to)

        # Total billed
        billed_query = select(func.sum(Bill.total_amount))
        if bill_conditions:
            billed_query = billed_query.where(and_(*bill_conditions))
        total_billed = await self.db.execute(billed_query)

        # Total collected
        collected_query = select(func.sum(Bill.paid_amount))
        if bill_conditions:
            collected_query = collected_query.where(and_(*bill_conditions))
        total_collected = await self.db.execute(collected_query)

        # Outstanding
        outstanding_query = select(func.sum(Bill.balance_amount)).where(
            Bill.status.in_([BillStatus.PENDING, BillStatus.PARTIALLY_PAID])
        )
        if bill_conditions:
            outstanding_query = outstanding_query.where(and_(*bill_conditions))
        total_outstanding = await self.db.execute(outstanding_query)

        # Bills by status
        status_query = (
            select(Bill.status, func.count(Bill.id))
            .group_by(Bill.status)
        )
        if bill_conditions:
            status_query = status_query.where(and_(*bill_conditions))
        status_result = await self.db.execute(status_query)
        by_status = {str(s.value): c for s, c in status_result.all()}

        # Payments by method
        payment_conditions = []
        if branch_id:
            payment_conditions.append(Bill.branch_id == branch_id)
        if date_from:
            payment_conditions.append(func.date(Payment.payment_date) >= date_from)
        if date_to:
            payment_conditions.append(func.date(Payment.payment_date) <= date_to)

        method_query = (
            select(Payment.payment_method, func.sum(Payment.amount))
            .join(Bill)
            .where(Payment.status == PaymentStatus.COMPLETED)
            .group_by(Payment.payment_method)
        )
        if payment_conditions:
            method_query = method_query.where(and_(*payment_conditions))
        method_result = await self.db.execute(method_query)
        by_method = {str(m.value): float(a) for m, a in method_result.all()}

        billed = total_billed.scalar() or Decimal("0.00")
        collected = total_collected.scalar() or Decimal("0.00")
        collection_rate = (collected / billed * 100) if billed > 0 else 0

        return {
            "total_billed": float(billed),
            "total_collected": float(collected),
            "total_outstanding": float(total_outstanding.scalar() or Decimal("0.00")),
            "collection_rate": round(float(collection_rate), 2),
            "pending_bills": by_status.get("pending", 0),
            "paid_bills": by_status.get("paid", 0),
            "by_status": by_status,
            "by_payment_method": by_method,
        }
