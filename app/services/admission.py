"""Admission service."""

from datetime import date, datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.models.enums import AdmissionStatus, BedStatus
from app.db.models.admission import Admission
from app.repositories.admission import AdmissionRepository
from app.repositories.room import BedRepository


class AdmissionService:
    """Admission management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.admission_repo = AdmissionRepository(db)
        self.bed_repo = BedRepository(db)

    async def get_admission(self, admission_id: UUID) -> Optional[Admission]:
        """Get admission by ID."""
        return await self.admission_repo.get_with_details(admission_id)

    async def get_admission_by_admission_id(
        self,
        admission_id: str,
    ) -> Optional[Admission]:
        """Get admission by auto-generated ID."""
        return await self.admission_repo.get_by_admission_id(admission_id)

    async def get_admissions(
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
        """Get list of admissions."""
        return await self.admission_repo.get_admissions_list(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            branch_id=branch_id,
            bed_id=bed_id,
            status=status,
            admission_date_from=admission_date_from,
            admission_date_to=admission_date_to,
            search=search,
        )

    async def count_admissions(
        self,
        *,
        patient_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[AdmissionStatus] = None,
    ) -> int:
        """Count admissions."""
        return await self.admission_repo.count_admissions(
            patient_id=patient_id,
            branch_id=branch_id,
            status=status,
        )

    async def admit_patient(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        branch_id: UUID,
        bed_id: UUID,
        admission_reason: str,
        admission_date: Optional[datetime] = None,
        expected_discharge_date: Optional[date] = None,
        diagnosis: Optional[str] = None,
        treatment_plan: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Admission:
        """Admit a patient."""
        # Check if patient already has active admission
        existing = await self.admission_repo.get_current_admission(patient_id)
        if existing:
            raise ConflictError("Patient already has an active admission")

        # Check bed availability
        bed = await self.bed_repo.get(bed_id)
        if not bed:
            raise NotFoundError("Bed not found")

        if bed.status != BedStatus.AVAILABLE:
            raise ValidationError("Bed is not available")

        # Assign bed to patient
        await self.bed_repo.assign_patient(bed_id, patient_id)

        # Create admission
        admission = await self.admission_repo.create({
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "branch_id": branch_id,
            "bed_id": bed_id,
            "admission_reason": admission_reason,
            "admission_date": admission_date or datetime.utcnow(),
            "expected_discharge_date": expected_discharge_date,
            "diagnosis": diagnosis,
            "treatment_plan": treatment_plan,
            "notes": notes,
            "status": AdmissionStatus.ADMITTED,
        })

        await self.db.commit()
        await self.db.refresh(admission)

        return admission

    async def update_admission(
        self,
        admission_id: UUID,
        **update_data,
    ) -> Optional[Admission]:
        """Update admission."""
        admission = await self.admission_repo.get(admission_id)
        if not admission:
            raise NotFoundError("Admission not found")

        if admission.status == AdmissionStatus.DISCHARGED:
            raise ValidationError("Cannot update discharged admission")

        updated = await self.admission_repo.update(admission_id, update_data)
        await self.db.commit()

        return updated

    async def discharge_patient(
        self,
        admission_id: UUID,
        discharge_notes: Optional[str] = None,
        discharge_instructions: Optional[str] = None,
    ) -> Optional[Admission]:
        """Discharge a patient."""
        admission = await self.admission_repo.get(admission_id)
        if not admission:
            raise NotFoundError("Admission not found")

        if admission.status != AdmissionStatus.ADMITTED:
            raise ValidationError("Patient is not currently admitted")

        # Release bed
        await self.bed_repo.release_bed(admission.bed_id, for_cleaning=True)

        # Update admission
        discharged = await self.admission_repo.discharge(
            admission_id,
            discharge_notes,
            discharge_instructions,
        )

        await self.db.commit()
        return discharged

    async def transfer_bed(
        self,
        admission_id: UUID,
        new_bed_id: UUID,
        reason: str,
    ) -> Optional[Admission]:
        """Transfer patient to a new bed."""
        admission = await self.admission_repo.get(admission_id)
        if not admission:
            raise NotFoundError("Admission not found")

        if admission.status != AdmissionStatus.ADMITTED:
            raise ValidationError("Patient is not currently admitted")

        # Check new bed availability
        new_bed = await self.bed_repo.get(new_bed_id)
        if not new_bed:
            raise NotFoundError("New bed not found")

        if new_bed.status != BedStatus.AVAILABLE:
            raise ValidationError("New bed is not available")

        # Release old bed
        await self.bed_repo.release_bed(admission.bed_id, for_cleaning=True)

        # Assign new bed
        await self.bed_repo.assign_patient(new_bed_id, admission.patient_id)

        # Update admission
        update_data = {
            "bed_id": new_bed_id,
            "notes": f"{admission.notes or ''}\nTransferred: {reason}".strip(),
        }

        updated = await self.admission_repo.update(admission_id, update_data)
        await self.db.commit()

        return updated

    async def extend_stay(
        self,
        admission_id: UUID,
        new_expected_discharge_date: date,
        reason: str,
    ) -> Optional[Admission]:
        """Extend expected discharge date."""
        admission = await self.admission_repo.get(admission_id)
        if not admission:
            raise NotFoundError("Admission not found")

        if admission.status != AdmissionStatus.ADMITTED:
            raise ValidationError("Patient is not currently admitted")

        update_data = {
            "expected_discharge_date": new_expected_discharge_date,
            "notes": f"{admission.notes or ''}\nStay extended: {reason}".strip(),
        }

        updated = await self.admission_repo.update(admission_id, update_data)
        await self.db.commit()

        return updated

    async def get_active_admissions(
        self,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[Admission]:
        """Get all active admissions."""
        return await self.admission_repo.get_active_admissions(branch_id)

    async def get_patient_admissions(
        self,
        patient_id: UUID,
        *,
        include_current: bool = True,
        limit: int = 50,
    ) -> Sequence[Admission]:
        """Get admissions for a patient."""
        return await self.admission_repo.get_patient_admissions(
            patient_id,
            include_current=include_current,
            limit=limit,
        )

    async def get_current_admission(
        self,
        patient_id: UUID,
    ) -> Optional[Admission]:
        """Get current active admission for a patient."""
        return await self.admission_repo.get_current_admission(patient_id)

    async def get_expected_discharges(
        self,
        target_date: date,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[Admission]:
        """Get admissions with expected discharge on a date."""
        return await self.admission_repo.get_expected_discharges(target_date, branch_id)

    async def get_admission_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get admission statistics."""
        return await self.admission_repo.get_admission_stats(branch_id)
