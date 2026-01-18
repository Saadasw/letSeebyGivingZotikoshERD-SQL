"""Lab test repository."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.enums import LabTestStatus, SampleStatus
from app.db.models.lab_test import LabTestType, LabTest, LabTestSample
from app.db.models.patient import PatientProfile
from app.db.models.doctor import DoctorProfile
from .base import BaseRepository


class LabTestTypeRepository(BaseRepository[LabTestType]):
    """Repository for LabTestType model."""

    def __init__(self, db: AsyncSession):
        super().__init__(LabTestType, db)

    async def get_by_code(self, code: str) -> Optional[LabTestType]:
        """Get test type by code."""
        query = select(LabTestType).where(LabTestType.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_test_types_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sample_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
    ) -> Sequence[LabTestType]:
        """Get list of test types with filters."""
        query = select(LabTestType)

        conditions = []

        if search:
            conditions.append(
                or_(
                    LabTestType.name.ilike(f"%{search}%"),
                    LabTestType.code.ilike(f"%{search}%"),
                )
            )
        if category:
            conditions.append(LabTestType.category == category)
        if sample_type:
            conditions.append(LabTestType.sample_type == sample_type)
        if is_active is not None:
            conditions.append(LabTestType.is_active == is_active)
        if min_price is not None:
            conditions.append(LabTestType.price >= min_price)
        if max_price is not None:
            conditions.append(LabTestType.price <= max_price)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(LabTestType.name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_categories(self) -> Sequence[str]:
        """Get all unique categories."""
        query = select(LabTestType.category).distinct()
        result = await self.db.execute(query)
        return [r[0] for r in result.all()]


class LabTestRepository(BaseRepository[LabTest]):
    """Repository for LabTest model."""

    def __init__(self, db: AsyncSession):
        super().__init__(LabTest, db)

    async def get_by_test_id(self, test_id: str) -> Optional[LabTest]:
        """Get lab test by auto-generated ID."""
        query = select(LabTest).where(LabTest.test_id == test_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[LabTest]:
        """Get lab test with related details."""
        query = (
            select(LabTest)
            .where(LabTest.id == id)
            .options(
                joinedload(LabTest.patient).joinedload(PatientProfile.user),
                joinedload(LabTest.doctor).joinedload(DoctorProfile.user),
                joinedload(LabTest.test_type),
                selectinload(LabTest.samples),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_tests_list(
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
        """Get list of lab tests with filters."""
        query = (
            select(LabTest)
            .options(
                joinedload(LabTest.patient).joinedload(PatientProfile.user),
                joinedload(LabTest.doctor).joinedload(DoctorProfile.user),
                joinedload(LabTest.test_type),
            )
        )

        conditions = []

        if patient_id:
            conditions.append(LabTest.patient_id == patient_id)
        if doctor_id:
            conditions.append(LabTest.doctor_id == doctor_id)
        if test_type_id:
            conditions.append(LabTest.test_type_id == test_type_id)
        if status:
            conditions.append(LabTest.status == status)
        if priority:
            conditions.append(LabTest.priority == priority)
        if is_abnormal is not None:
            conditions.append(LabTest.is_abnormal == is_abnormal)
        if date_from:
            conditions.append(func.date(LabTest.ordered_at) >= date_from)
        if date_to:
            conditions.append(func.date(LabTest.ordered_at) <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(LabTest.ordered_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_tests(
        self,
        *,
        patient_id: Optional[UUID] = None,
        status: Optional[LabTestStatus] = None,
    ) -> int:
        """Count lab tests matching filters."""
        query = select(func.count(LabTest.id))

        conditions = []
        if patient_id:
            conditions.append(LabTest.patient_id == patient_id)
        if status:
            conditions.append(LabTest.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_patient_tests(
        self,
        patient_id: UUID,
        *,
        pending_only: bool = False,
        limit: int = 50,
    ) -> Sequence[LabTest]:
        """Get lab tests for a patient."""
        query = (
            select(LabTest)
            .where(LabTest.patient_id == patient_id)
            .options(
                joinedload(LabTest.test_type),
                joinedload(LabTest.doctor).joinedload(DoctorProfile.user),
            )
        )

        if pending_only:
            query = query.where(
                LabTest.status.in_([
                    LabTestStatus.ORDERED,
                    LabTestStatus.SAMPLE_COLLECTED,
                    LabTestStatus.IN_PROGRESS,
                ])
            )

        query = query.order_by(LabTest.ordered_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        test_id: UUID,
        status: LabTestStatus,
        **kwargs,
    ) -> Optional[LabTest]:
        """Update lab test status."""
        update_data = {"status": status, **kwargs}

        if status == LabTestStatus.SAMPLE_COLLECTED:
            update_data["collected_at"] = datetime.utcnow()
        elif status == LabTestStatus.COMPLETED:
            update_data["results_at"] = datetime.utcnow()

        return await self.update(test_id, update_data)

    async def add_results(
        self,
        test_id: UUID,
        results: str,
        result_values: Optional[dict] = None,
        is_abnormal: bool = False,
        technician_notes: Optional[str] = None,
    ) -> Optional[LabTest]:
        """Add results to a lab test."""
        return await self.update(
            test_id,
            {
                "results": results,
                "result_values": result_values,
                "is_abnormal": is_abnormal,
                "technician_notes": technician_notes,
                "results_at": datetime.utcnow(),
                "status": LabTestStatus.COMPLETED,
            },
        )

    async def verify_results(
        self,
        test_id: UUID,
        verified_by: UUID,
    ) -> Optional[LabTest]:
        """Verify lab test results."""
        return await self.update(
            test_id,
            {
                "verified_by": verified_by,
                "verified_at": datetime.utcnow(),
                "status": LabTestStatus.VERIFIED,
            },
        )

    # Lab Test Samples
    async def create_sample(
        self,
        lab_test_id: UUID,
        sample_number: str,
        sample_type: str,
        collected_by: Optional[UUID] = None,
        volume: Optional[str] = None,
        collection_notes: Optional[str] = None,
    ) -> LabTestSample:
        """Create a lab test sample."""
        sample = LabTestSample(
            lab_test_id=lab_test_id,
            sample_number=sample_number,
            sample_type=sample_type,
            collected_by=collected_by,
            volume=volume,
            collection_notes=collection_notes,
        )
        self.db.add(sample)
        await self.db.flush()
        await self.db.refresh(sample)
        return sample

    async def get_test_samples(
        self,
        lab_test_id: UUID,
    ) -> Sequence[LabTestSample]:
        """Get samples for a lab test."""
        query = (
            select(LabTestSample)
            .where(LabTestSample.lab_test_id == lab_test_id)
            .order_by(LabTestSample.collected_at)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_lab_test_stats(self) -> dict[str, Any]:
        """Get lab test statistics."""
        # Total tests
        total_query = select(func.count(LabTest.id))
        total = await self.db.execute(total_query)

        # By status
        status_query = (
            select(LabTest.status, func.count(LabTest.id))
            .group_by(LabTest.status)
        )
        status_result = await self.db.execute(status_query)
        by_status = {str(s.value): c for s, c in status_result.all()}

        # Abnormal results
        abnormal_query = select(func.count(LabTest.id)).where(
            LabTest.is_abnormal == True
        )
        abnormal = await self.db.execute(abnormal_query)

        # By priority
        priority_query = (
            select(LabTest.priority, func.count(LabTest.id))
            .group_by(LabTest.priority)
        )
        priority_result = await self.db.execute(priority_query)
        by_priority = {p: c for p, c in priority_result.all()}

        return {
            "total_tests": total.scalar() or 0,
            "pending": by_status.get("ordered", 0) + by_status.get("sample_collected", 0) + by_status.get("in_progress", 0),
            "completed": by_status.get("completed", 0) + by_status.get("verified", 0),
            "abnormal_results": abnormal.scalar() or 0,
            "by_status": by_status,
            "by_priority": by_priority,
        }
