"""Prescription service."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.enums import PrescriptionStatus
from app.db.models.prescription import Prescription
from app.repositories.prescription import PrescriptionRepository
from app.repositories.inventory import InventoryRepository


class PrescriptionService:
    """Prescription management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.prescription_repo = PrescriptionRepository(db)
        self.inventory_repo = InventoryRepository(db)

    async def get_prescription(self, prescription_id: UUID) -> Optional[Prescription]:
        """Get prescription by ID."""
        return await self.prescription_repo.get_with_details(prescription_id)

    async def get_prescription_by_prescription_id(
        self,
        prescription_id: str,
    ) -> Optional[Prescription]:
        """Get prescription by auto-generated ID."""
        return await self.prescription_repo.get_by_prescription_id(prescription_id)

    async def get_prescriptions(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        appointment_id: Optional[UUID] = None,
        status: Optional[PrescriptionStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        is_expired: Optional[bool] = None,
    ) -> Sequence[Prescription]:
        """Get list of prescriptions with filters."""
        return await self.prescription_repo.get_prescriptions_list(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            is_expired=is_expired,
        )

    async def count_prescriptions(
        self,
        *,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        status: Optional[PrescriptionStatus] = None,
    ) -> int:
        """Count prescriptions matching filters."""
        return await self.prescription_repo.count_prescriptions(
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=status,
        )

    async def create_prescription(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        items: list[dict],
        appointment_id: Optional[UUID] = None,
        medical_record_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        valid_until: Optional[date] = None,
    ) -> Prescription:
        """Create a new prescription with items."""
        if not items:
            raise ValidationError("At least one prescription item is required")

        prescription = await self.prescription_repo.create_with_items(
            prescription_data={
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "appointment_id": appointment_id,
                "medical_record_id": medical_record_id,
                "notes": notes,
                "valid_until": valid_until,
                "status": PrescriptionStatus.ACTIVE,
            },
            items_data=items,
        )

        await self.db.commit()
        await self.db.refresh(prescription)

        return prescription

    async def update_prescription(
        self,
        prescription_id: UUID,
        **update_data,
    ) -> Optional[Prescription]:
        """Update prescription."""
        prescription = await self.prescription_repo.get(prescription_id)
        if not prescription:
            raise NotFoundError("Prescription not found")

        if prescription.status == PrescriptionStatus.COMPLETED:
            raise ValidationError("Cannot update completed prescription")

        updated = await self.prescription_repo.update(prescription_id, update_data)
        await self.db.commit()

        return updated

    async def cancel_prescription(
        self,
        prescription_id: UUID,
    ) -> Optional[Prescription]:
        """Cancel prescription."""
        return await self.update_prescription(
            prescription_id,
            status=PrescriptionStatus.CANCELLED,
        )

    async def get_patient_prescriptions(
        self,
        patient_id: UUID,
        *,
        active_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Prescription]:
        """Get prescriptions for a patient."""
        return await self.prescription_repo.get_patient_prescriptions(
            patient_id,
            active_only=active_only,
            limit=limit,
        )

    async def get_prescription_items(
        self,
        prescription_id: UUID,
    ):
        """Get items for a prescription."""
        return await self.prescription_repo.get_prescription_items(prescription_id)

    async def dispense_item(
        self,
        prescription_item_id: UUID,
        quantity: int,
        branch_id: UUID,
        dispensed_by: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Dispense a prescription item from inventory."""
        item = await self.prescription_repo.get_item(prescription_item_id)
        if not item:
            raise NotFoundError("Prescription item not found")

        # Check available quantity
        remaining = item.quantity - item.dispensed_quantity
        if quantity > remaining:
            raise ValidationError(f"Cannot dispense more than {remaining} units")

        # Get inventory for the medicine
        inventory = await self.inventory_repo.get_by_medicine_branch(
            item.medicine_id, branch_id
        )

        if not inventory:
            raise NotFoundError("Medicine not found in inventory at this branch")

        if inventory.quantity < quantity:
            raise ValidationError("Insufficient stock")

        # Reduce inventory
        await self.inventory_repo.adjust_quantity(inventory.id, -quantity)

        # Create dispense log
        await self.inventory_repo.create_dispense_log(
            inventory_id=inventory.id,
            quantity=quantity,
            dispensed_by=dispensed_by,
            prescription_id=item.prescription_id,
            prescription_item_id=prescription_item_id,
            batch_number=inventory.batch_number,
            unit_price=inventory.selling_price,
            notes=notes,
        )

        # Update dispensed quantity
        await self.prescription_repo.update_item_dispensed(prescription_item_id, quantity)

        # Check if all items dispensed
        all_dispensed = await self.prescription_repo.check_all_items_dispensed(
            item.prescription_id
        )

        if all_dispensed:
            await self.prescription_repo.update_status(
                item.prescription_id,
                PrescriptionStatus.COMPLETED,
            )

        await self.db.commit()
        return True

    async def dispense_prescription(
        self,
        prescription_id: UUID,
        branch_id: UUID,
        items: list[dict],
        dispensed_by: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Dispense multiple items from a prescription."""
        prescription = await self.prescription_repo.get(prescription_id)
        if not prescription:
            raise NotFoundError("Prescription not found")

        dispensed = []
        failed = []

        for item in items:
            try:
                await self.dispense_item(
                    prescription_item_id=item["prescription_item_id"],
                    quantity=item["quantity"],
                    branch_id=branch_id,
                    dispensed_by=dispensed_by,
                    notes=notes,
                )
                dispensed.append(item)
            except Exception as e:
                failed.append({
                    **item,
                    "error": str(e),
                })

        return {
            "prescription_id": prescription_id,
            "dispensed": dispensed,
            "failed": failed,
            "total_dispensed": len(dispensed),
            "total_failed": len(failed),
        }
