"""Patient service."""

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import get_password_hash
from app.db.models.enums import BloodGroup, Gender, UserRole
from app.db.models.patient import PatientProfile
from app.repositories.patient import PatientRepository
from app.repositories.user import UserRepository


class PatientService:
    """Patient management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.user_repo = UserRepository(db)

    async def get_patient(self, patient_id: UUID) -> Optional[PatientProfile]:
        """Get patient by ID."""
        return await self.patient_repo.get_with_user(patient_id)

    async def get_patient_by_user_id(self, user_id: UUID) -> Optional[PatientProfile]:
        """Get patient by user ID."""
        return await self.patient_repo.get_by_user_id(user_id)

    async def get_patient_by_patient_id(self, patient_id: str) -> Optional[PatientProfile]:
        """Get patient by auto-generated patient ID."""
        return await self.patient_repo.get_by_patient_id(patient_id)

    async def get_patients(
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
        return await self.patient_repo.get_patients_list(
            skip=skip,
            limit=limit,
            search=search,
            gender=gender,
            blood_group=blood_group,
            has_insurance=has_insurance,
            city=city,
            is_active=is_active,
        )

    async def count_patients(
        self,
        *,
        search: Optional[str] = None,
        gender: Optional[Gender] = None,
        blood_group: Optional[BloodGroup] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count patients matching filters."""
        return await self.patient_repo.count_patients(
            search=search,
            gender=gender,
            blood_group=blood_group,
            is_active=is_active,
        )

    async def create_patient(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        **patient_data,
    ) -> PatientProfile:
        """Create a new patient with user account."""
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            from app.core.exceptions import ConflictError
            raise ConflictError("Email already registered")

        # Create user
        user = await self.user_repo.create({
            "email": email,
            "hashed_password": get_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "role": UserRole.PATIENT,
            "is_active": True,
            "is_verified": False,
        })

        # Create patient profile
        patient = await self.patient_repo.create({
            "user_id": user.id,
            **patient_data,
        })

        await self.db.commit()
        await self.db.refresh(patient)

        return patient

    async def create_patient_profile(
        self,
        user_id: UUID,
        **patient_data,
    ) -> PatientProfile:
        """Create patient profile for existing user."""
        # Check if user exists
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Check if profile already exists
        existing = await self.patient_repo.get_by_user_id(user_id)
        if existing:
            from app.core.exceptions import ConflictError
            raise ConflictError("Patient profile already exists")

        patient = await self.patient_repo.create({
            "user_id": user_id,
            **patient_data,
        })

        await self.db.commit()
        await self.db.refresh(patient)

        return patient

    async def update_patient(
        self,
        patient_id: UUID,
        **update_data,
    ) -> Optional[PatientProfile]:
        """Update patient profile."""
        patient = await self.patient_repo.get(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        updated = await self.patient_repo.update(patient_id, update_data)
        await self.db.commit()

        return updated

    async def get_patient_medical_summary(
        self,
        patient_id: UUID,
    ) -> dict[str, Any]:
        """Get patient's medical summary."""
        patient = await self.patient_repo.get_with_user(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        # Get recent diagnoses from medical records
        from app.repositories.medical_record import MedicalRecordRepository
        from app.repositories.prescription import PrescriptionRepository
        from app.repositories.lab_test import LabTestRepository
        from app.db.models.enums import PrescriptionStatus, LabTestStatus

        mr_repo = MedicalRecordRepository(self.db)
        rx_repo = PrescriptionRepository(self.db)
        lab_repo = LabTestRepository(self.db)

        records = await mr_repo.get_patient_records(patient_id, limit=5)
        diagnoses = [r.diagnosis for r in records if r.diagnosis]

        active_rx = await rx_repo.count_prescriptions(
            patient_id=patient_id,
            status=PrescriptionStatus.ACTIVE,
        )

        pending_labs = await lab_repo.count_tests(
            patient_id=patient_id,
            status=LabTestStatus.ORDERED,
        )

        return {
            "patient_id": patient_id,
            "allergies": patient.allergies,
            "chronic_conditions": patient.chronic_conditions,
            "current_medications": patient.current_medications,
            "blood_group": patient.blood_group,
            "recent_diagnoses": diagnoses[:5],
            "active_prescriptions": active_rx,
            "pending_lab_tests": pending_labs,
        }

    async def get_patient_insurance_info(
        self,
        patient_id: UUID,
    ) -> dict[str, Any]:
        """Get patient's insurance information."""
        patient = await self.patient_repo.get(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        from datetime import date

        is_valid = False
        if patient.insurance_expiry:
            is_valid = patient.insurance_expiry >= date.today()

        return {
            "insurance_provider": patient.insurance_provider,
            "insurance_policy_number": patient.insurance_policy_number,
            "insurance_expiry": patient.insurance_expiry,
            "is_valid": is_valid and patient.insurance_provider is not None,
        }

    async def get_patient_emergency_info(
        self,
        patient_id: UUID,
    ) -> dict[str, Any]:
        """Get patient's emergency information."""
        patient = await self.patient_repo.get_with_user(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        return {
            "patient_id": patient_id,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "blood_group": patient.blood_group,
            "allergies": patient.allergies,
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_phone": patient.emergency_contact_phone,
            "emergency_contact_relation": patient.emergency_contact_relation,
            "chronic_conditions": patient.chronic_conditions,
            "current_medications": patient.current_medications,
        }

    async def get_patients_by_blood_group(
        self,
        blood_group: BloodGroup,
        *,
        limit: int = 100,
    ) -> Sequence[PatientProfile]:
        """Get patients by blood group."""
        return await self.patient_repo.get_patients_by_blood_group(
            blood_group,
            limit=limit,
        )

    async def check_doctor_patient_access(
        self,
        patient_id: UUID,
        doctor_id: UUID,
    ) -> bool:
        """Check if doctor has access to patient."""
        return await self.patient_repo.check_patient_access(patient_id, doctor_id)

    async def get_patient_stats(self) -> dict[str, Any]:
        """Get patient statistics."""
        return await self.patient_repo.get_patient_stats()
