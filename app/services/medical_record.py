"""Medical record service."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, AuthorizationError
from app.db.models.medical_record import MedicalRecord, Vitals
from app.repositories.medical_record import MedicalRecordRepository, VitalsRepository


class MedicalRecordService:
    """Medical record management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.record_repo = MedicalRecordRepository(db)
        self.vitals_repo = VitalsRepository(db)

    async def get_record(self, record_id: UUID) -> Optional[MedicalRecord]:
        """Get medical record by ID."""
        return await self.record_repo.get_with_details(record_id)

    async def get_record_by_record_id(self, record_id: str) -> Optional[MedicalRecord]:
        """Get medical record by auto-generated ID."""
        return await self.record_repo.get_by_record_id(record_id)

    async def get_records(
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
        return await self.record_repo.get_records_list(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            admission_id=admission_id,
            search=search,
            date_from=date_from,
            date_to=date_to,
            is_confidential=is_confidential,
        )

    async def count_records(
        self,
        *,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
    ) -> int:
        """Count medical records."""
        return await self.record_repo.count_records(
            patient_id=patient_id,
            doctor_id=doctor_id,
        )

    async def create_record(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        chief_complaint: str,
        appointment_id: Optional[UUID] = None,
        admission_id: Optional[UUID] = None,
        **record_data,
    ) -> MedicalRecord:
        """Create a new medical record."""
        record = await self.record_repo.create({
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "chief_complaint": chief_complaint,
            "appointment_id": appointment_id,
            "admission_id": admission_id,
            "version": 1,
            **record_data,
        })

        await self.db.commit()
        await self.db.refresh(record)

        return record

    async def update_record(
        self,
        record_id: UUID,
        updated_by: UUID,
        **update_data,
    ) -> Optional[MedicalRecord]:
        """Update medical record with version history."""
        record = await self.record_repo.get(record_id)
        if not record:
            raise NotFoundError("Medical record not found")

        # Store old values for history
        old_values = {
            key: getattr(record, key)
            for key in update_data.keys()
            if hasattr(record, key)
        }

        # Create history entry
        await self.record_repo.create_history_entry(
            medical_record_id=record_id,
            version=record.version,
            changed_by=updated_by,
            changes={
                "old": old_values,
                "new": update_data,
            },
        )

        # Update record
        update_data["version"] = record.version + 1
        updated = await self.record_repo.update(record_id, update_data)

        await self.db.commit()
        return updated

    async def get_patient_records(
        self,
        patient_id: UUID,
        *,
        include_confidential: bool = False,
        limit: int = 50,
    ) -> Sequence[MedicalRecord]:
        """Get medical records for a patient."""
        return await self.record_repo.get_patient_records(
            patient_id,
            include_confidential=include_confidential,
            limit=limit,
        )

    async def get_by_appointment(
        self,
        appointment_id: UUID,
    ) -> Optional[MedicalRecord]:
        """Get medical record for an appointment."""
        return await self.record_repo.get_by_appointment(appointment_id)

    async def get_record_history(
        self,
        record_id: UUID,
    ):
        """Get history for a medical record."""
        return await self.record_repo.get_record_history(record_id)

    async def check_doctor_access(
        self,
        record_id: UUID,
        doctor_id: UUID,
    ) -> bool:
        """Check if doctor has access to a medical record."""
        return await self.record_repo.check_doctor_access(record_id, doctor_id)

    # Vitals
    async def get_vitals(self, vitals_id: UUID) -> Optional[Vitals]:
        """Get vitals by ID."""
        return await self.vitals_repo.get(vitals_id)

    async def get_patient_vitals(
        self,
        patient_id: UUID,
        *,
        limit: int = 10,
    ) -> Sequence[Vitals]:
        """Get recent vitals for a patient."""
        return await self.vitals_repo.get_patient_vitals(patient_id, limit=limit)

    async def get_latest_vitals(
        self,
        patient_id: UUID,
    ) -> Optional[Vitals]:
        """Get the most recent vitals for a patient."""
        return await self.vitals_repo.get_latest_vitals(patient_id)

    async def record_vitals(
        self,
        patient_id: UUID,
        recorded_by: Optional[UUID] = None,
        **vitals_data,
    ) -> Vitals:
        """Record patient vitals."""
        vitals = await self.vitals_repo.create({
            "patient_id": patient_id,
            "recorded_by": recorded_by,
            **vitals_data,
        })

        await self.db.commit()
        await self.db.refresh(vitals)

        return vitals

    async def get_vitals_by_date_range(
        self,
        patient_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Sequence[Vitals]:
        """Get vitals within a date range."""
        return await self.vitals_repo.get_vitals_by_date_range(
            patient_id, start_date, end_date
        )
