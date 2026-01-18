"""Medical record repository."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.medical_record import MedicalRecord, MedicalRecordHistory, Vitals
from app.db.models.patient import PatientProfile
from app.db.models.doctor import DoctorProfile
from app.db.models.user import User
from .base import BaseRepository


class VitalsRepository(BaseRepository[Vitals]):
    """Repository for Vitals model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Vitals, db)

    async def get_patient_vitals(
        self,
        patient_id: UUID,
        *,
        limit: int = 10,
    ) -> Sequence[Vitals]:
        """Get recent vitals for a patient."""
        query = (
            select(Vitals)
            .where(Vitals.patient_id == patient_id)
            .order_by(Vitals.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_latest_vitals(
        self,
        patient_id: UUID,
    ) -> Optional[Vitals]:
        """Get the most recent vitals for a patient."""
        query = (
            select(Vitals)
            .where(Vitals.patient_id == patient_id)
            .order_by(Vitals.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_vitals_by_date_range(
        self,
        patient_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Sequence[Vitals]:
        """Get vitals within a date range."""
        query = (
            select(Vitals)
            .where(
                and_(
                    Vitals.patient_id == patient_id,
                    func.date(Vitals.created_at) >= start_date,
                    func.date(Vitals.created_at) <= end_date,
                )
            )
            .order_by(Vitals.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()


class MedicalRecordRepository(BaseRepository[MedicalRecord]):
    """Repository for MedicalRecord model."""

    def __init__(self, db: AsyncSession):
        super().__init__(MedicalRecord, db)

    async def get_by_record_id(self, record_id: str) -> Optional[MedicalRecord]:
        """Get medical record by auto-generated ID."""
        query = select(MedicalRecord).where(MedicalRecord.record_id == record_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[MedicalRecord]:
        """Get medical record with related details."""
        query = (
            select(MedicalRecord)
            .where(MedicalRecord.id == id)
            .options(
                joinedload(MedicalRecord.patient).joinedload(PatientProfile.user),
                joinedload(MedicalRecord.doctor).joinedload(DoctorProfile.user),
                joinedload(MedicalRecord.appointment),
                selectinload(MedicalRecord.history),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_records_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        appointment_id: Optional[UUID] = None,
        admission_id: Optional[UUID] = None,
        search: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        is_confidential: Optional[bool] = None,
    ) -> Sequence[MedicalRecord]:
        """Get list of medical records with filters."""
        query = (
            select(MedicalRecord)
            .options(
                joinedload(MedicalRecord.patient).joinedload(PatientProfile.user),
                joinedload(MedicalRecord.doctor).joinedload(DoctorProfile.user),
            )
        )

        conditions = []

        if patient_id:
            conditions.append(MedicalRecord.patient_id == patient_id)
        if doctor_id:
            conditions.append(MedicalRecord.doctor_id == doctor_id)
        if appointment_id:
            conditions.append(MedicalRecord.appointment_id == appointment_id)
        if admission_id:
            conditions.append(MedicalRecord.admission_id == admission_id)
        if is_confidential is not None:
            conditions.append(MedicalRecord.is_confidential == is_confidential)
        if date_from:
            conditions.append(func.date(MedicalRecord.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(MedicalRecord.created_at) <= date_to)

        if search:
            conditions.append(
                or_(
                    MedicalRecord.diagnosis.ilike(f"%{search}%"),
                    MedicalRecord.chief_complaint.ilike(f"%{search}%"),
                    MedicalRecord.record_id.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(MedicalRecord.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_records(
        self,
        *,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
    ) -> int:
        """Count medical records."""
        query = select(func.count(MedicalRecord.id))

        conditions = []
        if patient_id:
            conditions.append(MedicalRecord.patient_id == patient_id)
        if doctor_id:
            conditions.append(MedicalRecord.doctor_id == doctor_id)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_patient_records(
        self,
        patient_id: UUID,
        *,
        include_confidential: bool = False,
        limit: int = 50,
    ) -> Sequence[MedicalRecord]:
        """Get medical records for a patient."""
        query = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .options(
                joinedload(MedicalRecord.doctor).joinedload(DoctorProfile.user),
            )
        )

        if not include_confidential:
            query = query.where(MedicalRecord.is_confidential == False)

        query = query.order_by(MedicalRecord.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_appointment(
        self,
        appointment_id: UUID,
    ) -> Optional[MedicalRecord]:
        """Get medical record for an appointment."""
        query = (
            select(MedicalRecord)
            .where(MedicalRecord.appointment_id == appointment_id)
            .options(
                joinedload(MedicalRecord.doctor).joinedload(DoctorProfile.user),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_history_entry(
        self,
        medical_record_id: UUID,
        version: int,
        changed_by: UUID,
        changes: dict,
    ) -> MedicalRecordHistory:
        """Create a history entry for a medical record."""
        history = MedicalRecordHistory(
            medical_record_id=medical_record_id,
            version=version,
            changed_by=changed_by,
            changes=changes,
        )
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_record_history(
        self,
        medical_record_id: UUID,
    ) -> Sequence[MedicalRecordHistory]:
        """Get history for a medical record."""
        query = (
            select(MedicalRecordHistory)
            .where(MedicalRecordHistory.medical_record_id == medical_record_id)
            .order_by(MedicalRecordHistory.version.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def check_doctor_access(
        self,
        record_id: UUID,
        doctor_id: UUID,
    ) -> bool:
        """Check if doctor has access to a medical record."""
        record = await self.get(record_id)
        if not record:
            return False

        # Doctor created the record
        if record.doctor_id == doctor_id:
            return True

        # Check if doctor has treated this patient
        from app.db.models.appointment import Appointment

        apt_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == record.patient_id,
                Appointment.doctor_id == doctor_id,
            )
        )
        result = await self.db.execute(apt_query)
        return (result.scalar() or 0) > 0
