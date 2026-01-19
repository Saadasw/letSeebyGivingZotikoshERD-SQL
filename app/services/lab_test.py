"""Lab test service."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.enums import LabTestStatus
from app.db.models.lab_test import LabTest, LabTestType
from app.repositories.lab_test import LabTestRepository, LabTestTypeRepository


class LabTestService:
    """Lab test management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.test_repo = LabTestRepository(db)
        self.type_repo = LabTestTypeRepository(db)

    # Test Types
    async def get_test_type(self, type_id: UUID) -> Optional[LabTestType]:
        """Get test type by ID."""
        return await self.type_repo.get(type_id)

    async def get_test_type_by_code(self, code: str) -> Optional[LabTestType]:
        """Get test type by code."""
        return await self.type_repo.get_by_code(code)

    async def get_test_types(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sample_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[LabTestType]:
        """Get list of test types."""
        return await self.type_repo.get_test_types_list(
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            sample_type=sample_type,
            is_active=is_active,
        )

    async def create_test_type(self, **type_data) -> LabTestType:
        """Create a new test type."""
        test_type = await self.type_repo.create(type_data)
        await self.db.commit()
        await self.db.refresh(test_type)
        return test_type

    async def update_test_type(
        self,
        type_id: UUID,
        **update_data,
    ) -> Optional[LabTestType]:
        """Update test type."""
        updated = await self.type_repo.update(type_id, update_data)
        await self.db.commit()
        return updated

    async def get_test_categories(self) -> Sequence[str]:
        """Get all test categories."""
        return await self.type_repo.get_categories()

    # Lab Tests
    async def get_test(self, test_id: UUID) -> Optional[LabTest]:
        """Get lab test by ID."""
        return await self.test_repo.get_with_details(test_id)

    async def get_test_by_test_id(self, test_id: str) -> Optional[LabTest]:
        """Get lab test by auto-generated ID."""
        return await self.test_repo.get_by_test_id(test_id)

    async def get_tests(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        test_type_id: Optional[UUID] = None,
        status: Optional[LabTestStatus] = None,
        priority: Optional[str] = None,
        is_abnormal: Optional[bool] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Sequence[LabTest]:
        """Get list of lab tests."""
        return await self.test_repo.get_tests_list(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            test_type_id=test_type_id,
            status=status,
            priority=priority,
            is_abnormal=is_abnormal,
            date_from=date_from,
            date_to=date_to,
        )

    async def count_tests(
        self,
        *,
        patient_id: Optional[UUID] = None,
        status: Optional[LabTestStatus] = None,
    ) -> int:
        """Count lab tests."""
        return await self.test_repo.count_tests(
            patient_id=patient_id,
            status=status,
        )

    async def order_test(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        test_type_id: UUID,
        priority: str = "normal",
        appointment_id: Optional[UUID] = None,
        admission_id: Optional[UUID] = None,
        clinical_notes: Optional[str] = None,
    ) -> LabTest:
        """Order a new lab test."""
        # Validate test type
        test_type = await self.type_repo.get(test_type_id)
        if not test_type or not test_type.is_active:
            raise NotFoundError("Test type not found or inactive")

        test = await self.test_repo.create({
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_type_id": test_type_id,
            "priority": priority,
            "appointment_id": appointment_id,
            "admission_id": admission_id,
            "clinical_notes": clinical_notes,
            "status": LabTestStatus.ORDERED,
        })

        await self.db.commit()
        await self.db.refresh(test)

        return test

    async def collect_sample(
        self,
        test_id: UUID,
        sample_number: str,
        sample_type: str,
        collected_by: Optional[UUID] = None,
        volume: Optional[str] = None,
        collection_notes: Optional[str] = None,
    ):
        """Collect sample for a lab test."""
        test = await self.test_repo.get(test_id)
        if not test:
            raise NotFoundError("Lab test not found")

        if test.status != LabTestStatus.ORDERED:
            raise ValidationError("Sample can only be collected for ordered tests")

        # Create sample record
        sample = await self.test_repo.create_sample(
            lab_test_id=test_id,
            sample_number=sample_number,
            sample_type=sample_type,
            collected_by=collected_by,
            volume=volume,
            collection_notes=collection_notes,
        )

        # Update test status
        await self.test_repo.update_status(test_id, LabTestStatus.SAMPLE_COLLECTED)

        await self.db.commit()
        return sample

    async def start_processing(self, test_id: UUID) -> Optional[LabTest]:
        """Start processing a lab test."""
        test = await self.test_repo.get(test_id)
        if not test:
            raise NotFoundError("Lab test not found")

        if test.status != LabTestStatus.SAMPLE_COLLECTED:
            raise ValidationError("Sample must be collected first")

        updated = await self.test_repo.update_status(test_id, LabTestStatus.IN_PROGRESS)
        await self.db.commit()

        return updated

    async def add_results(
        self,
        test_id: UUID,
        results: str,
        result_values: Optional[dict] = None,
        is_abnormal: bool = False,
        technician_notes: Optional[str] = None,
    ) -> Optional[LabTest]:
        """Add results to a lab test."""
        test = await self.test_repo.get(test_id)
        if not test:
            raise NotFoundError("Lab test not found")

        if test.status not in [LabTestStatus.SAMPLE_COLLECTED, LabTestStatus.IN_PROGRESS]:
            raise ValidationError("Test is not ready for results")

        updated = await self.test_repo.add_results(
            test_id,
            results,
            result_values,
            is_abnormal,
            technician_notes,
        )

        await self.db.commit()
        return updated

    async def verify_results(
        self,
        test_id: UUID,
        verified_by: UUID,
    ) -> Optional[LabTest]:
        """Verify lab test results."""
        test = await self.test_repo.get(test_id)
        if not test:
            raise NotFoundError("Lab test not found")

        if test.status != LabTestStatus.COMPLETED:
            raise ValidationError("Results must be completed first")

        updated = await self.test_repo.verify_results(test_id, verified_by)
        await self.db.commit()

        return updated

    async def get_patient_tests(
        self,
        patient_id: UUID,
        *,
        pending_only: bool = False,
        limit: int = 50,
    ) -> Sequence[LabTest]:
        """Get lab tests for a patient."""
        return await self.test_repo.get_patient_tests(
            patient_id,
            pending_only=pending_only,
            limit=limit,
        )

    async def get_test_samples(self, test_id: UUID):
        """Get samples for a lab test."""
        return await self.test_repo.get_test_samples(test_id)

    async def get_lab_test_stats(self) -> dict[str, Any]:
        """Get lab test statistics."""
        return await self.test_repo.get_lab_test_stats()
