"""Admission repository."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.enums import AdmissionStatus
from app.db.models.admission import Admission
from app.db.models.patient import PatientProfile
from app.db.models.doctor import DoctorProfile
from app.db.models.room import Room, Bed
from .base import BaseRepository


class AdmissionRepository(BaseRepository[Admission]):
    """Repository for Admission model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Admission, db)

    async def get_by_admission_id(self, admission_id: str) -> Optional[Admission]:
        """Get admission by auto-generated ID."""
        query = select(Admission).where(Admission.admission_id == admission_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[Admission]:
        """Get admission with related details."""
        query = (
            select(Admission)
            .where(Admission.id == id)
            .options(
                joinedload(Admission.patient).joinedload(PatientProfile.user),
                joinedload(Admission.doctor).joinedload(DoctorProfile.user),
                joinedload(Admission.branch),
                joinedload(Admission.bed).joinedload(Bed.room),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_admissions_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        bed_id: Optional[UUID] = None,
        status: Optional[AdmissionStatus] = None,
        admission_date_from: Optional[date] = None,
        admission_date_to: Optional[date] = None,
        search: Optional[str] = None,
    ) -> Sequence[Admission]:
        """Get list of admissions with filters."""
        query = (
            select(Admission)
            .options(
                joinedload(Admission.patient).joinedload(PatientProfile.user),
                joinedload(Admission.doctor).joinedload(DoctorProfile.user),
                joinedload(Admission.branch),
                joinedload(Admission.bed).joinedload(Bed.room),
            )
        )

        conditions = []

        if patient_id:
            conditions.append(Admission.patient_id == patient_id)
        if doctor_id:
            conditions.append(Admission.doctor_id == doctor_id)
        if branch_id:
            conditions.append(Admission.branch_id == branch_id)
        if bed_id:
            conditions.append(Admission.bed_id == bed_id)
        if status:
            conditions.append(Admission.status == status)
        if admission_date_from:
            conditions.append(func.date(Admission.admission_date) >= admission_date_from)
        if admission_date_to:
            conditions.append(func.date(Admission.admission_date) <= admission_date_to)

        if search:
            query = query.join(
                PatientProfile, Admission.patient_id == PatientProfile.id
            ).join(
                User, PatientProfile.user_id == User.id
            )
            from app.db.models.user import User
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    Admission.admission_id.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Admission.admission_date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_admissions(
        self,
        *,
        patient_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[AdmissionStatus] = None,
    ) -> int:
        """Count admissions matching filters."""
        query = select(func.count(Admission.id))

        conditions = []
        if patient_id:
            conditions.append(Admission.patient_id == patient_id)
        if branch_id:
            conditions.append(Admission.branch_id == branch_id)
        if status:
            conditions.append(Admission.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_active_admissions(
        self,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[Admission]:
        """Get all active admissions."""
        query = (
            select(Admission)
            .where(Admission.status == AdmissionStatus.ADMITTED)
            .options(
                joinedload(Admission.patient).joinedload(PatientProfile.user),
                joinedload(Admission.doctor).joinedload(DoctorProfile.user),
                joinedload(Admission.bed).joinedload(Bed.room),
            )
        )

        if branch_id:
            query = query.where(Admission.branch_id == branch_id)

        query = query.order_by(Admission.admission_date.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_patient_admissions(
        self,
        patient_id: UUID,
        *,
        include_current: bool = True,
        limit: int = 50,
    ) -> Sequence[Admission]:
        """Get admissions for a patient."""
        query = (
            select(Admission)
            .where(Admission.patient_id == patient_id)
            .options(
                joinedload(Admission.doctor).joinedload(DoctorProfile.user),
                joinedload(Admission.bed).joinedload(Bed.room),
            )
        )

        if not include_current:
            query = query.where(Admission.status != AdmissionStatus.ADMITTED)

        query = query.order_by(Admission.admission_date.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_current_admission(
        self,
        patient_id: UUID,
    ) -> Optional[Admission]:
        """Get current active admission for a patient."""
        query = (
            select(Admission)
            .where(
                and_(
                    Admission.patient_id == patient_id,
                    Admission.status == AdmissionStatus.ADMITTED,
                )
            )
            .options(
                joinedload(Admission.bed).joinedload(Bed.room),
                joinedload(Admission.doctor).joinedload(DoctorProfile.user),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def discharge(
        self,
        admission_id: UUID,
        discharge_notes: Optional[str] = None,
        discharge_instructions: Optional[str] = None,
    ) -> Optional[Admission]:
        """Discharge a patient."""
        return await self.update(
            admission_id,
            {
                "status": AdmissionStatus.DISCHARGED,
                "discharge_date": datetime.utcnow(),
                "discharge_notes": discharge_notes,
                "discharge_instructions": discharge_instructions,
            },
        )

    async def transfer_bed(
        self,
        admission_id: UUID,
        new_bed_id: UUID,
    ) -> Optional[Admission]:
        """Transfer patient to a new bed."""
        return await self.update(admission_id, {"bed_id": new_bed_id})

    async def get_expected_discharges(
        self,
        target_date: date,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[Admission]:
        """Get admissions with expected discharge on a date."""
        query = (
            select(Admission)
            .where(
                and_(
                    Admission.status == AdmissionStatus.ADMITTED,
                    Admission.expected_discharge_date == target_date,
                )
            )
            .options(
                joinedload(Admission.patient).joinedload(PatientProfile.user),
                joinedload(Admission.bed).joinedload(Bed.room),
            )
        )

        if branch_id:
            query = query.where(Admission.branch_id == branch_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_admission_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get admission statistics."""
        today = date.today()

        base_conditions = []
        if branch_id:
            base_conditions.append(Admission.branch_id == branch_id)

        # Total admissions
        total_query = select(func.count(Admission.id))
        if base_conditions:
            total_query = total_query.where(and_(*base_conditions))
        total = await self.db.execute(total_query)

        # Active admissions
        active_query = select(func.count(Admission.id)).where(
            and_(*base_conditions, Admission.status == AdmissionStatus.ADMITTED)
            if base_conditions
            else Admission.status == AdmissionStatus.ADMITTED
        )
        active = await self.db.execute(active_query)

        # Discharged today
        discharged_query = select(func.count(Admission.id)).where(
            and_(
                *base_conditions,
                Admission.status == AdmissionStatus.DISCHARGED,
                func.date(Admission.discharge_date) == today,
            )
            if base_conditions
            else and_(
                Admission.status == AdmissionStatus.DISCHARGED,
                func.date(Admission.discharge_date) == today,
            )
        )
        discharged = await self.db.execute(discharged_query)

        # Expected discharges today
        expected_query = select(func.count(Admission.id)).where(
            and_(
                *base_conditions,
                Admission.status == AdmissionStatus.ADMITTED,
                Admission.expected_discharge_date == today,
            )
            if base_conditions
            else and_(
                Admission.status == AdmissionStatus.ADMITTED,
                Admission.expected_discharge_date == today,
            )
        )
        expected = await self.db.execute(expected_query)

        # Average stay days
        avg_query = select(
            func.avg(
                func.extract(
                    "day",
                    Admission.discharge_date - Admission.admission_date,
                )
            )
        ).where(Admission.status == AdmissionStatus.DISCHARGED)
        if base_conditions:
            avg_query = avg_query.where(and_(*base_conditions))
        avg_stay = await self.db.execute(avg_query)

        # By status
        status_query = (
            select(Admission.status, func.count(Admission.id))
            .group_by(Admission.status)
        )
        if base_conditions:
            status_query = status_query.where(and_(*base_conditions))
        status_result = await self.db.execute(status_query)
        by_status = {str(s.value): c for s, c in status_result.all()}

        return {
            "total_admissions": total.scalar() or 0,
            "active_admissions": active.scalar() or 0,
            "discharged_today": discharged.scalar() or 0,
            "expected_discharges_today": expected.scalar() or 0,
            "average_stay_days": float(avg_stay.scalar() or 0),
            "by_status": by_status,
        }
