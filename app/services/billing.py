"""Billing service."""

from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.enums import BillStatus, PaymentMethod, PaymentStatus
from app.db.models.billing import Bill, Payment
from app.repositories.billing import BillRepository, PaymentRepository


class BillingService:
    """Billing management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.bill_repo = BillRepository(db)
        self.payment_repo = PaymentRepository(db)

    # Bills
    async def get_bill(self, bill_id: UUID) -> Optional[Bill]:
        """Get bill by ID."""
        return await self.bill_repo.get_with_details(bill_id)

    async def get_bill_by_number(self, bill_number: str) -> Optional[Bill]:
        """Get bill by number."""
        return await self.bill_repo.get_by_bill_number(bill_number)

    async def get_bills(
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
        """Get list of bills."""
        return await self.bill_repo.get_bills_list(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            branch_id=branch_id,
            appointment_id=appointment_id,
            admission_id=admission_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            is_overdue=is_overdue,
            search=search,
        )

    async def count_bills(
        self,
        *,
        patient_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[BillStatus] = None,
    ) -> int:
        """Count bills."""
        return await self.bill_repo.count_bills(
            patient_id=patient_id,
            branch_id=branch_id,
            status=status,
        )

    async def create_bill(
        self,
        patient_id: UUID,
        branch_id: UUID,
        items: list[dict],
        appointment_id: Optional[UUID] = None,
        admission_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        due_date: Optional[date] = None,
        discount_percent: Decimal = Decimal("0.00"),
        generated_by: Optional[UUID] = None,
    ) -> Bill:
        """Create a new bill."""
        bill = await self.bill_repo.create_with_items(
            bill_data={
                "patient_id": patient_id,
                "branch_id": branch_id,
                "appointment_id": appointment_id,
                "admission_id": admission_id,
                "notes": notes,
                "due_date": due_date,
                "discount_percent": discount_percent,
                "generated_by": generated_by,
                "status": BillStatus.PENDING,
            },
            items_data=items,
        )

        await self.db.commit()
        await self.db.refresh(bill)

        return bill

    async def update_bill(
        self,
        bill_id: UUID,
        **update_data,
    ) -> Optional[Bill]:
        """Update bill."""
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise NotFoundError("Bill not found")

        if bill.status in [BillStatus.PAID, BillStatus.CANCELLED]:
            raise ValidationError("Cannot update paid or cancelled bill")

        updated = await self.bill_repo.update(bill_id, update_data)
        await self.db.commit()

        return updated

    async def update_bill_status(
        self,
        bill_id: UUID,
        status: BillStatus,
        reason: Optional[str] = None,
    ) -> Optional[Bill]:
        """Update bill status."""
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise NotFoundError("Bill not found")

        update_data = {"status": status}
        if reason:
            update_data["notes"] = f"{bill.notes or ''}\n{reason}".strip()

        updated = await self.bill_repo.update(bill_id, update_data)
        await self.db.commit()

        return updated

    async def cancel_bill(
        self,
        bill_id: UUID,
        reason: str,
    ) -> Optional[Bill]:
        """Cancel a bill."""
        return await self.update_bill_status(
            bill_id,
            BillStatus.CANCELLED,
            f"Cancelled: {reason}",
        )

    async def get_patient_bills(
        self,
        patient_id: UUID,
        *,
        pending_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Bill]:
        """Get bills for a patient."""
        return await self.bill_repo.get_patient_bills(
            patient_id,
            pending_only=pending_only,
            limit=limit,
        )

    # Payments
    async def get_payment(self, payment_id: UUID) -> Optional[Payment]:
        """Get payment by ID."""
        return await self.payment_repo.get_with_bill(payment_id)

    async def get_payment_by_payment_id(
        self,
        payment_id: str,
    ) -> Optional[Payment]:
        """Get payment by auto-generated ID."""
        return await self.payment_repo.get_by_payment_id(payment_id)

    async def get_payments(
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
        """Get list of payments."""
        return await self.payment_repo.get_payments_list(
            skip=skip,
            limit=limit,
            bill_id=bill_id,
            patient_id=patient_id,
            branch_id=branch_id,
            payment_method=payment_method,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

    async def record_payment(
        self,
        bill_id: UUID,
        amount: Decimal,
        payment_method: PaymentMethod,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        processed_by: Optional[UUID] = None,
    ) -> Payment:
        """Record a payment for a bill."""
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise NotFoundError("Bill not found")

        if bill.status == BillStatus.CANCELLED:
            raise ValidationError("Cannot pay cancelled bill")

        if amount > bill.balance_amount:
            raise ValidationError(
                f"Payment amount exceeds balance. Maximum: {bill.balance_amount}"
            )

        # Create payment
        payment = await self.payment_repo.create({
            "bill_id": bill_id,
            "amount": amount,
            "payment_method": payment_method,
            "reference_number": reference_number,
            "notes": notes,
            "processed_by": processed_by,
            "status": PaymentStatus.COMPLETED,
        })

        # Update bill amounts
        await self.bill_repo.add_payment(bill_id, amount)

        await self.db.commit()
        await self.db.refresh(payment)

        return payment

    async def get_bill_payments(self, bill_id: UUID) -> Sequence[Payment]:
        """Get all payments for a bill."""
        return await self.payment_repo.get_bill_payments(bill_id)

    async def refund_payment(
        self,
        payment_id: UUID,
        amount: Decimal,
        reason: str,
        refunded_by: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Process a refund for a payment."""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")

        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError("Can only refund completed payments")

        if amount > payment.amount:
            raise ValidationError("Refund amount exceeds payment amount")

        # Update payment status
        await self.payment_repo.update(
            payment_id,
            {
                "status": PaymentStatus.REFUNDED,
                "notes": f"{payment.notes or ''}\nRefunded: {reason}".strip(),
            },
        )

        # Update bill - add back to balance
        await self.bill_repo.update(
            payment.bill_id,
            {
                "paid_amount": Bill.paid_amount - amount,
                "balance_amount": Bill.balance_amount + amount,
                "status": BillStatus.PENDING,
            },
        )

        await self.db.commit()

        return {
            "payment_id": payment_id,
            "refund_amount": amount,
            "reason": reason,
            "refunded_by": refunded_by,
        }

    async def get_billing_stats(
        self,
        branch_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        """Get billing statistics."""
        return await self.payment_repo.get_billing_stats(
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_patient_billing_summary(
        self,
        patient_id: UUID,
    ) -> dict[str, Any]:
        """Get billing summary for a patient."""
        bills = await self.bill_repo.get_patient_bills(patient_id)

        total_billed = sum(b.total_amount for b in bills)
        total_paid = sum(b.paid_amount for b in bills)
        outstanding = sum(
            b.balance_amount
            for b in bills
            if b.status in [BillStatus.PENDING, BillStatus.PARTIALLY_PAID]
        )

        today = date.today()
        overdue = sum(
            b.balance_amount
            for b in bills
            if b.status in [BillStatus.PENDING, BillStatus.PARTIALLY_PAID]
            and b.due_date
            and b.due_date < today
        )

        payments = await self.payment_repo.get_payments_list(
            patient_id=patient_id,
            status=PaymentStatus.COMPLETED,
            limit=1,
        )

        return {
            "patient_id": patient_id,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "outstanding_balance": outstanding,
            "overdue_amount": overdue,
            "last_payment_date": payments[0].payment_date if payments else None,
        }
