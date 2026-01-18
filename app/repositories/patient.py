"""Patient repository."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.db.models.enums import BloodGroup, Gender
from app.db.models.patient import PatientProfile
from app.db.models.user import User
from .base import BaseRepository


class PatientRepository(BaseRepository[PatientProfile]):
    """Repository for PatientProfile model."""

    def __init__(self, db: AsyncSession):
        super().__init__(PatientProfile, db)

    async def get_by_user_id(self, user_id: UUID) -> Optional[PatientProfile]:
        """Get patient profile by user ID."""
        query = (
            select(PatientProfile)
            .where(PatientProfile.user_id == user_id)
            .options(joinedload(PatientProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_patient_id(self, patient_id: str) -> Optional[PatientProfile]:
        """Get patient profile by auto-generated patient ID."""
        query = (
            select(PatientProfile)
            .where(PatientProfile.patient_id == patient_id)
            .options(joinedload(PatientProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_user(self, id: UUID) -> Optional[PatientProfile]:
        """Get patient profile with user details."""
        query = (
            select(PatientProfile)
            .where(PatientProfile.id == id)
            .options(joinedload(PatientProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_patients_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        gender: Optional[Gender] = None,
        blood_group: Optional[BloodGroup] = None,
        has_insurance: Optional[bool] = None,
        city: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[PatientProfile]:
        """Get list of patients with filters."""
        query = (
            select(PatientProfile)
            .join(User)
            .options(joinedload(PatientProfile.user))
        )

        conditions = []

        if search:
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    PatientProfile.patient_id.ilike(f"%{search}%"),
                )
            )

        if gender:
            conditions.append(PatientProfile.gender == gender)

        if blood_group:
            conditions.append(PatientProfile.blood_group == blood_group)

        if has_insurance is not None:
            if has_insurance:
                conditions.append(PatientProfile.insurance_provider.isnot(None))
            else:
                conditions.append(PatientProfile.insurance_provider.is_(None))

        if city:
            conditions.append(PatientProfile.city.ilike(f"%{city}%"))

        if is_active is not None:
            conditions.append(User.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(PatientProfile.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_patients(
        self,
        *,
        search: Optional[str] = None,
        gender: Optional[Gender] = None,
        blood_group: Optional[BloodGroup] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count patients matching filters."""
        query = select(func.count(PatientProfile.id)).join(User)

        conditions = []

        if search:
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    PatientProfile.patient_id.ilike(f"%{search}%"),
                )
            )

        if gender:
            conditions.append(PatientProfile.gender == gender)

        if blood_group:
            conditions.append(PatientProfile.blood_group == blood_group)

        if is_active is not None:
            conditions.append(User.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_patients_by_blood_group(
        self,
        blood_group: BloodGroup,
        *,
        limit: int = 100,
    ) -> Sequence[PatientProfile]:
        """Get patients by blood group."""
        query = (
            select(PatientProfile)
            .where(PatientProfile.blood_group == blood_group)
            .join(User)
            .where(User.is_active == True)
            .options(joinedload(PatientProfile.user))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_patients_by_age_range(
        self,
        min_age: int,
        max_age: int,
        *,
        limit: int = 100,
    ) -> Sequence[PatientProfile]:
        """Get patients within an age range."""
        today = date.today()
        max_birth_date = date(today.year - min_age, today.month, today.day)
        min_birth_date = date(today.year - max_age - 1, today.month, today.day)

        query = (
            select(PatientProfile)
            .where(
                and_(
                    PatientProfile.date_of_birth >= min_birth_date,
                    PatientProfile.date_of_birth <= max_birth_date,
                )
            )
            .join(User)
            .where(User.is_active == True)
            .options(joinedload(PatientProfile.user))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_patient_stats(self) -> dict[str, Any]:
        """Get patient statistics."""
        # Total patients
        total_query = select(func.count(PatientProfile.id))
        total = await self.db.execute(total_query)

        # By gender
        gender_query = (
            select(PatientProfile.gender, func.count(PatientProfile.id))
            .where(PatientProfile.gender.isnot(None))
            .group_by(PatientProfile.gender)
        )
        gender_result = await self.db.execute(gender_query)
        by_gender = {str(g.value): c for g, c in gender_result.all() if g}

        # By blood group
        blood_query = (
            select(PatientProfile.blood_group, func.count(PatientProfile.id))
            .where(PatientProfile.blood_group.isnot(None))
            .group_by(PatientProfile.blood_group)
        )
        blood_result = await self.db.execute(blood_query)
        by_blood_group = {str(b.value): c for b, c in blood_result.all() if b}

        # With insurance
        insured_query = select(func.count(PatientProfile.id)).where(
            PatientProfile.insurance_provider.isnot(None)
        )
        insured = await self.db.execute(insured_query)

        return {
            "total_patients": total.scalar() or 0,
            "by_gender": by_gender,
            "by_blood_group": by_blood_group,
            "with_insurance": insured.scalar() or 0,
        }

    async def check_patient_access(
        self,
        patient_id: UUID,
        doctor_id: UUID,
    ) -> bool:
        """Check if doctor has access to patient via appointments or records."""
        from app.db.models.appointment import Appointment
        from app.db.models.medical_record import MedicalRecord

        # Check appointments
        apt_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.doctor_id == doctor_id,
            )
        )
        apt_result = await self.db.execute(apt_query)

        if (apt_result.scalar() or 0) > 0:
            return True

        # Check medical records
        mr_query = select(func.count(MedicalRecord.id)).where(
            and_(
                MedicalRecord.patient_id == patient_id,
                MedicalRecord.doctor_id == doctor_id,
            )
        )
        mr_result = await self.db.execute(mr_query)

        return (mr_result.scalar() or 0) > 0
