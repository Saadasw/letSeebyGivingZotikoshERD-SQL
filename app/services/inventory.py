"""Inventory service."""

from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.models.enums import InventoryTransactionType
from app.db.models.medicine import Medicine
from app.db.models.inventory import Inventory
from app.repositories.inventory import MedicineRepository, InventoryRepository


class InventoryService:
    """Inventory management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.medicine_repo = MedicineRepository(db)
        self.inventory_repo = InventoryRepository(db)

    # Medicines
    async def get_medicine(self, medicine_id: UUID) -> Optional[Medicine]:
        """Get medicine by ID."""
        return await self.medicine_repo.get(medicine_id)

    async def get_medicine_by_code(self, code: str) -> Optional[Medicine]:
        """Get medicine by code."""
        return await self.medicine_repo.get_by_code(code)

    async def get_medicines(
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
        """Get list of medicines."""
        return await self.medicine_repo.get_medicines_list(
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            dosage_form=dosage_form,
            requires_prescription=requires_prescription,
            is_active=is_active,
        )

    async def create_medicine(self, **medicine_data) -> Medicine:
        """Create a new medicine."""
        medicine = await self.medicine_repo.create(medicine_data)
        await self.db.commit()
        await self.db.refresh(medicine)
        return medicine

    async def update_medicine(
        self,
        medicine_id: UUID,
        **update_data,
    ) -> Optional[Medicine]:
        """Update medicine."""
        updated = await self.medicine_repo.update(medicine_id, update_data)
        await self.db.commit()
        return updated

    async def get_medicine_categories(self) -> Sequence[str]:
        """Get all medicine categories."""
        return await self.medicine_repo.get_categories()

    # Inventory
    async def get_inventory(self, inventory_id: UUID) -> Optional[Inventory]:
        """Get inventory by ID."""
        return await self.inventory_repo.get_with_medicine(inventory_id)

    async def get_inventory_by_medicine_branch(
        self,
        medicine_id: UUID,
        branch_id: UUID,
    ) -> Optional[Inventory]:
        """Get inventory for a medicine at a branch."""
        return await self.inventory_repo.get_by_medicine_branch(medicine_id, branch_id)

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
        """Get list of inventory."""
        return await self.inventory_repo.get_inventory_list(
            skip=skip,
            limit=limit,
            medicine_id=medicine_id,
            branch_id=branch_id,
            search=search,
            category=category,
            is_low_stock=is_low_stock,
            is_expired=is_expired,
            is_expiring_soon=is_expiring_soon,
            is_active=is_active,
        )

    async def add_to_inventory(
        self,
        medicine_id: UUID,
        branch_id: UUID,
        quantity: int,
        unit_price: Decimal,
        selling_price: Decimal,
        batch_number: Optional[str] = None,
        expiry_date: Optional[date] = None,
        supplier: Optional[str] = None,
        reorder_level: int = 10,
        max_stock_level: int = 1000,
        location: Optional[str] = None,
    ) -> Inventory:
        """Add medicine to inventory."""
        # Check if medicine exists
        medicine = await self.medicine_repo.get(medicine_id)
        if not medicine:
            raise NotFoundError("Medicine not found")

        # Check if inventory exists for this medicine at branch
        existing = await self.inventory_repo.get_by_medicine_branch(
            medicine_id, branch_id
        )

        if existing:
            # Update existing inventory
            await self.inventory_repo.update_restock(existing.id, quantity)
            updated = await self.inventory_repo.update(
                existing.id,
                {
                    "unit_price": unit_price,
                    "selling_price": selling_price,
                    "batch_number": batch_number,
                    "expiry_date": expiry_date,
                    "supplier": supplier,
                },
            )
            await self.db.commit()
            return updated

        # Create new inventory
        inventory = await self.inventory_repo.create({
            "medicine_id": medicine_id,
            "branch_id": branch_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "selling_price": selling_price,
            "batch_number": batch_number,
            "expiry_date": expiry_date,
            "supplier": supplier,
            "reorder_level": reorder_level,
            "max_stock_level": max_stock_level,
            "location": location,
        })

        await self.db.commit()
        await self.db.refresh(inventory)

        return inventory

    async def adjust_stock(
        self,
        inventory_id: UUID,
        quantity: int,
        transaction_type: InventoryTransactionType,
        reason: str,
        adjusted_by: Optional[UUID] = None,
        reference_number: Optional[str] = None,
    ) -> dict[str, Any]:
        """Adjust inventory stock."""
        inventory = await self.inventory_repo.get(inventory_id)
        if not inventory:
            raise NotFoundError("Inventory not found")

        # Validate quantity change
        if transaction_type in [
            InventoryTransactionType.SALE,
            InventoryTransactionType.DISPENSE,
            InventoryTransactionType.DAMAGE,
            InventoryTransactionType.EXPIRED,
        ]:
            if quantity > 0:
                quantity = -quantity  # Make it negative for deductions

        new_quantity = inventory.quantity + quantity
        if new_quantity < 0:
            raise ValidationError("Insufficient stock for this adjustment")

        previous_quantity = inventory.quantity

        # Perform adjustment
        await self.inventory_repo.adjust_quantity(inventory_id, quantity)
        await self.db.commit()

        return {
            "inventory_id": inventory_id,
            "previous_quantity": previous_quantity,
            "adjusted_quantity": quantity,
            "new_quantity": new_quantity,
            "transaction_type": transaction_type,
        }

    async def get_low_stock_items(
        self,
        branch_id: Optional[UUID] = None,
        *,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """Get items with low stock."""
        return await self.inventory_repo.get_low_stock_items(branch_id, limit=limit)

    async def get_expiring_items(
        self,
        branch_id: Optional[UUID] = None,
        days: int = 30,
        *,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """Get items expiring within specified days."""
        return await self.inventory_repo.get_expiring_items(
            branch_id, days, limit=limit
        )

    async def get_expired_items(
        self,
        branch_id: Optional[UUID] = None,
        *,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """Get expired items."""
        return await self.inventory_repo.get_expired_items(branch_id, limit=limit)

    async def get_stock_alerts(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get stock alerts (low, expired, expiring)."""
        low_stock = await self.get_low_stock_items(branch_id, limit=50)
        expired = await self.get_expired_items(branch_id, limit=50)
        expiring_soon = await self.get_expiring_items(branch_id, 30, limit=50)

        return {
            "low_stock": low_stock,
            "expired": expired,
            "expiring_soon": expiring_soon,
        }

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
    ):
        """Get dispense logs."""
        return await self.inventory_repo.get_dispense_logs(
            inventory_id=inventory_id,
            patient_id=patient_id,
            prescription_id=prescription_id,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )

    async def get_inventory_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get inventory statistics."""
        return await self.inventory_repo.get_inventory_stats(branch_id)
