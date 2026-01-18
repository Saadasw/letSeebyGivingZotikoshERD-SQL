"""Prescription repository."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.enums import PrescriptionStatus
from app.db.models.prescription import Prescription, PrescriptionItem
from app.db.models.patient import PatientProfile
from app.db.models.doctor import DoctorProfile
from app.db.models.user import User
from .base import BaseRepository


class PrescriptionRepository(BaseRepository[Prescription]):
    """Repository for Prescription model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Prescription, db)

    async def get_by_prescription_id(self, prescription_id: str) -> Optional[Prescription]:
        """Get prescription by auto-generated ID."""
        query = select(Prescription).where(Prescription.prescription_id == prescription_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[Prescription]:
        """Get prescription with items and related details."""
        query = (
            select(Prescription)
            .where(Prescription.id == id)
            .options(
                joinedload(Prescription.patient).joinedload(PatientProfile.user),
                joinedload(Prescription.doctor).joinedload(DoctorProfile.user),
                selectinload(Prescription.items).joinedload(PrescriptionItem.medicine),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_prescriptions_list(
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
        query = (
            select(Prescription)
            .options(
                joinedload(Prescription.patient).joinedload(PatientProfile.user),
                joinedload(Prescription.doctor).joinedload(DoctorProfile.user),
                selectinload(Prescription.items),
            )
        )

        conditions = []

        if patient_id:
            conditions.append(Prescription.patient_id == patient_id)
        if doctor_id:
            conditions.append(Prescription.doctor_id == doctor_id)
        if appointment_id:
            conditions.append(Prescription.appointment_id == appointment_id)
        if status:
            conditions.append(Prescription.status == status)
        if date_from:
            conditions.append(func.date(Prescription.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(Prescription.created_at) <= date_to)

        if is_expired is not None:
            today = date.today()
            if is_expired:
                conditions.append(
                    and_(
                        Prescription.valid_until.isnot(None),
                        Prescription.valid_until < today,
                    )
                )
            else:
                conditions.append(
                    or_(
                        Prescription.valid_until.is_(None),
                        Prescription.valid_until >= today,
                    )
                )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Prescription.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_prescriptions(
        self,
        *,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        status: Optional[PrescriptionStatus] = None,
    ) -> int:
        """Count prescriptions matching filters."""
        query = select(func.count(Prescription.id))

        conditions = []
        if patient_id:
            conditions.append(Prescription.patient_id == patient_id)
        if doctor_id:
            conditions.append(Prescription.doctor_id == doctor_id)
        if status:
            conditions.append(Prescription.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_patient_prescriptions(
        self,
        patient_id: UUID,
        *,
        active_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Prescription]:
        """Get prescriptions for a patient."""
        query = (
            select(Prescription)
            .where(Prescription.patient_id == patient_id)
            .options(
                joinedload(Prescription.doctor).joinedload(DoctorProfile.user),
                selectinload(Prescription.items).joinedload(PrescriptionItem.medicine),
            )
        )

        if active_only:
            today = date.today()
            query = query.where(
                and_(
                    Prescription.status == PrescriptionStatus.ACTIVE,
                    or_(
                        Prescription.valid_until.is_(None),
                        Prescription.valid_until >= today,
                    ),
                )
            )

        query = query.order_by(Prescription.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_appointment(
        self,
        appointment_id: UUID,
    ) -> Sequence[Prescription]:
        """Get prescriptions for an appointment."""
        query = (
            select(Prescription)
            .where(Prescription.appointment_id == appointment_id)
            .options(
                selectinload(Prescription.items).joinedload(PrescriptionItem.medicine),
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_with_items(
        self,
        prescription_data: dict,
        items_data: list[dict],
    ) -> Prescription:
        """Create prescription with items."""
        prescription = Prescription(**prescription_data)
        self.db.add(prescription)
        await self.db.flush()

        for item_data in items_data:
            item = PrescriptionItem(
                prescription_id=prescription.id,
                **item_data,
            )
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(prescription)
        return prescription

    async def update_status(
        self,
        prescription_id: UUID,
        status: PrescriptionStatus,
    ) -> Optional[Prescription]:
        """Update prescription status."""
        return await self.update(prescription_id, {"status": status})

    # Prescription Items
    async def get_item(self, item_id: UUID) -> Optional[PrescriptionItem]:
        """Get a prescription item."""
        query = (
            select(PrescriptionItem)
            .where(PrescriptionItem.id == item_id)
            .options(joinedload(PrescriptionItem.medicine))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_prescription_items(
        self,
        prescription_id: UUID,
    ) -> Sequence[PrescriptionItem]:
        """Get items for a prescription."""
        query = (
            select(PrescriptionItem)
            .where(PrescriptionItem.prescription_id == prescription_id)
            .options(joinedload(PrescriptionItem.medicine))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_item_dispensed(
        self,
        item_id: UUID,
        quantity: int,
    ) -> bool:
        """Update dispensed quantity for an item."""
        result = await self.db.execute(
            update(PrescriptionItem)
            .where(PrescriptionItem.id == item_id)
            .values(
                dispensed_quantity=PrescriptionItem.dispensed_quantity + quantity,
                is_dispensed=PrescriptionItem.dispensed_quantity + quantity >= PrescriptionItem.quantity,
            )
        )
        await self.db.flush()
        return result.rowcount > 0

    async def check_all_items_dispensed(
        self,
        prescription_id: UUID,
    ) -> bool:
        """Check if all items in a prescription are dispensed."""
        query = select(func.count(PrescriptionItem.id)).where(
            and_(
                PrescriptionItem.prescription_id == prescription_id,
                PrescriptionItem.is_dispensed == False,
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) == 0
