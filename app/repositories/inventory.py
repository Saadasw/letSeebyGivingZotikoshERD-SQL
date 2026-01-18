"""Inventory repository."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.medicine import Medicine
from app.db.models.inventory import Inventory, DispenseLog
from .base import BaseRepository


class MedicineRepository(BaseRepository[Medicine]):
    """Repository for Medicine model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Medicine, db)

    async def get_by_code(self, medicine_code: str) -> Optional[Medicine]:
        """Get medicine by auto-generated code."""
        query = select(Medicine).where(Medicine.medicine_code == medicine_code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_medicines_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None,
        dosage_form: Optional[str] = None,
        requires_prescription: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[Medicine]:
        """Get list of medicines with filters."""
        query = select(Medicine)

        conditions = []

        if search:
            conditions.append(
                or_(
                    Medicine.name.ilike(f"%{search}%"),
                    Medicine.generic_name.ilike(f"%{search}%"),
                    Medicine.medicine_code.ilike(f"%{search}%"),
                )
            )
        if category:
            conditions.append(Medicine.category == category)
        if dosage_form:
            conditions.append(Medicine.dosage_form == dosage_form)
        if requires_prescription is not None:
            conditions.append(Medicine.requires_prescription == requires_prescription)
        if is_active is not None:
            conditions.append(Medicine.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Medicine.name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_categories(self) -> Sequence[str]:
        """Get all unique categories."""
        query = select(Medicine.category).distinct()
        result = await self.db.execute(query)
        return [r[0] for r in result.all()]


class InventoryRepository(BaseRepository[Inventory]):
    """Repository for Inventory model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Inventory, db)

    async def get_with_medicine(self, id: UUID) -> Optional[Inventory]:
        """Get inventory with medicine details."""
        query = (
            select(Inventory)
            .where(Inventory.id == id)
            .options(joinedload(Inventory.medicine))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_medicine_branch(
        self,
        medicine_id: UUID,
        branch_id: UUID,
    ) -> Optional[Inventory]:
        """Get inventory for a medicine at a branch."""
        query = (
            select(Inventory)
            .where(
                and_(
                    Inventory.medicine_id == medicine_id,
                    Inventory.branch_id == branch_id,
                    Inventory.is_active == True,
                )
            )
            .options(joinedload(Inventory.medicine))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_inventory_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        medicine_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_low_stock: Optional[bool] = None,
        is_expired: Optional[bool] = None,
        is_expiring_soon: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[Inventory]:
        """Get list of inventory with filters."""
        query = (
            select(Inventory)
            .join(Medicine)
            .options(joinedload(Inventory.medicine))
        )

        conditions = []

        if medicine_id:
            conditions.append(Inventory.medicine_id == medicine_id)
        if branch_id:
            conditions.append(Inventory.branch_id == branch_id)
        if is_active is not None:
            conditions.append(Inventory.is_active == is_active)

        if search:
            conditions.append(
                or_(
                    Medicine.name.ilike(f"%{search}%"),
                    Medicine.generic_name.ilike(f"%{search}%"),
                    Medicine.medicine_code.ilike(f"%{search}%"),
                )
            )

        if category:
            conditions.append(Medicine.category == category)

        today = date.today()

        if is_low_stock:
            conditions.append(Inventory.quantity <= Inventory.reorder_level)

        if is_expired:
            conditions.append(
                and_(
                    Inventory.expiry_date.isnot(None),
                    Inventory.expiry_date < today,
                )
            )

        if is_expiring_soon:
            soon = today + timedelta(days=30)
            conditions.append(
                and_(
                    Inventory.expiry_date.isnot(None),
                    Inventory.expiry_date <= soon,
                    Inventory.expiry_date >= today,
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Medicine.name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def get_low_stock_items(
        self,
        branch_id: Optional[UUID] = None,
        *,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """Get items with low stock."""
        query = (
            select(Inventory)
            .where(
                and_(
                    Inventory.is_active == True,
                    Inventory.quantity <= Inventory.reorder_level,
                )
            )
            .options(joinedload(Inventory.medicine))
        )

        if branch_id:
            query = query.where(Inventory.branch_id == branch_id)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_expiring_items(
        self,
        branch_id: Optional[UUID] = None,
        days: int = 30,
        *,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """Get items expiring within specified days."""
        today = date.today()
        expiry_date = today + timedelta(days=days)

        query = (
            select(Inventory)
            .where(
                and_(
                    Inventory.is_active == True,
                    Inventory.expiry_date.isnot(None),
                    Inventory.expiry_date <= expiry_date,
                    Inventory.expiry_date >= today,
                )
            )
            .options(joinedload(Inventory.medicine))
        )

        if branch_id:
            query = query.where(Inventory.branch_id == branch_id)

        query = query.order_by(Inventory.expiry_date).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_expired_items(
        self,
        branch_id: Optional[UUID] = None,
        *,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """Get expired items."""
        today = date.today()

        query = (
            select(Inventory)
            .where(
                and_(
                    Inventory.is_active == True,
                    Inventory.expiry_date.isnot(None),
                    Inventory.expiry_date < today,
                )
            )
            .options(joinedload(Inventory.medicine))
        )

        if branch_id:
            query = query.where(Inventory.branch_id == branch_id)

        query = query.order_by(Inventory.expiry_date).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def adjust_quantity(
        self,
        inventory_id: UUID,
        quantity_change: int,
    ) -> bool:
        """Adjust inventory quantity."""
        result = await self.db.execute(
            update(Inventory)
            .where(
                and_(
                    Inventory.id == inventory_id,
                    Inventory.quantity + quantity_change >= 0,
                )
            )
            .values(quantity=Inventory.quantity + quantity_change)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def update_restock(
        self,
        inventory_id: UUID,
        quantity: int,
    ) -> bool:
        """Update quantity and last restocked time."""
        result = await self.db.execute(
            update(Inventory)
            .where(Inventory.id == inventory_id)
            .values(
                quantity=Inventory.quantity + quantity,
                last_restocked=datetime.utcnow(),
            )
        )
        await self.db.flush()
        return result.rowcount > 0

    # Dispense Log
    async def create_dispense_log(
        self,
        inventory_id: UUID,
        quantity: int,
        dispensed_by: Optional[UUID] = None,
        prescription_id: Optional[UUID] = None,
        prescription_item_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        batch_number: Optional[str] = None,
        unit_price: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
    ) -> DispenseLog:
        """Create a dispense log entry."""
        log = DispenseLog(
            inventory_id=inventory_id,
            quantity=quantity,
            dispensed_by=dispensed_by,
            prescription_id=prescription_id,
            prescription_item_id=prescription_item_id,
            patient_id=patient_id,
            batch_number=batch_number,
            unit_price=unit_price,
            total_price=unit_price * quantity,
            notes=notes,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_dispense_logs(
        self,
        *,
        inventory_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        prescription_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[DispenseLog]:
        """Get dispense logs with filters."""
        query = select(DispenseLog)

        conditions = []

        if inventory_id:
            conditions.append(DispenseLog.inventory_id == inventory_id)
        if patient_id:
            conditions.append(DispenseLog.patient_id == patient_id)
        if prescription_id:
            conditions.append(DispenseLog.prescription_id == prescription_id)
        if date_from:
            conditions.append(func.date(DispenseLog.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(DispenseLog.created_at) <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(DispenseLog.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_inventory_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get inventory statistics."""
        today = date.today()
        soon = today + timedelta(days=30)

        base_conditions = [Inventory.is_active == True]
        if branch_id:
            base_conditions.append(Inventory.branch_id == branch_id)

        # Total items
        total_query = select(func.count(Inventory.id)).where(and_(*base_conditions))
        total = await self.db.execute(total_query)

        # Total stock value
        value_query = select(
            func.sum(Inventory.quantity * Inventory.unit_price)
        ).where(and_(*base_conditions))
        total_value = await self.db.execute(value_query)

        # Low stock
        low_stock_query = select(func.count(Inventory.id)).where(
            and_(*base_conditions, Inventory.quantity <= Inventory.reorder_level)
        )
        low_stock = await self.db.execute(low_stock_query)

        # Out of stock
        out_of_stock_query = select(func.count(Inventory.id)).where(
            and_(*base_conditions, Inventory.quantity == 0)
        )
        out_of_stock = await self.db.execute(out_of_stock_query)

        # Expired
        expired_query = select(func.count(Inventory.id)).where(
            and_(
                *base_conditions,
                Inventory.expiry_date.isnot(None),
                Inventory.expiry_date < today,
            )
        )
        expired = await self.db.execute(expired_query)

        # Expiring soon
        expiring_query = select(func.count(Inventory.id)).where(
            and_(
                *base_conditions,
                Inventory.expiry_date.isnot(None),
                Inventory.expiry_date <= soon,
                Inventory.expiry_date >= today,
            )
        )
        expiring = await self.db.execute(expiring_query)

        return {
            "total_items": total.scalar() or 0,
            "total_stock_value": total_value.scalar() or Decimal("0.00"),
            "low_stock_items": low_stock.scalar() or 0,
            "out_of_stock_items": out_of_stock.scalar() or 0,
            "expired_items": expired.scalar() or 0,
            "expiring_soon_items": expiring.scalar() or 0,
        }
