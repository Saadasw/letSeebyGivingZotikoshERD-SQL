"""Doctor repository."""

from datetime import date, time
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.db.models.enums import DayOfWeek, Specialization
from app.db.models.doctor import (
    DoctorProfile,
    DoctorBranchAssignment,
    DoctorWeeklySchedule,
    DoctorScheduleOverride,
)
from app.db.models.user import User
from .base import BaseRepository


class DoctorRepository(BaseRepository[DoctorProfile]):
    """Repository for DoctorProfile model."""

    def __init__(self, db: AsyncSession):
        super().__init__(DoctorProfile, db)

    async def get_by_user_id(self, user_id: UUID) -> Optional[DoctorProfile]:
        """Get doctor profile by user ID."""
        query = (
            select(DoctorProfile)
            .where(DoctorProfile.user_id == user_id)
            .options(joinedload(DoctorProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_doctor_id(self, doctor_id: str) -> Optional[DoctorProfile]:
        """Get doctor profile by auto-generated doctor ID."""
        query = (
            select(DoctorProfile)
            .where(DoctorProfile.doctor_id == doctor_id)
            .options(joinedload(DoctorProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[DoctorProfile]:
        """Get doctor profile with user and branch assignments."""
        query = (
            select(DoctorProfile)
            .where(DoctorProfile.id == id)
            .options(
                joinedload(DoctorProfile.user),
                selectinload(DoctorProfile.branch_assignments),
                selectinload(DoctorProfile.schedules),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_doctors_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        specialization: Optional[Specialization] = None,
        branch_id: Optional[UUID] = None,
        is_available: Optional[bool] = None,
        min_experience: Optional[int] = None,
    ) -> Sequence[DoctorProfile]:
        """Get list of doctors with filters."""
        query = (
            select(DoctorProfile)
            .join(User)
            .options(joinedload(DoctorProfile.user))
        )

        conditions = [User.is_active == True]

        if search:
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    DoctorProfile.doctor_id.ilike(f"%{search}%"),
                )
            )

        if specialization:
            conditions.append(DoctorProfile.specialization == specialization)

        if is_available is not None:
            conditions.append(DoctorProfile.is_available == is_available)

        if min_experience is not None:
            conditions.append(DoctorProfile.experience_years >= min_experience)

        if branch_id:
            # Join with branch assignments
            query = query.join(
                DoctorBranchAssignment,
                DoctorProfile.id == DoctorBranchAssignment.doctor_id,
            ).where(DoctorBranchAssignment.branch_id == branch_id)

        query = query.where(and_(*conditions))
        query = query.order_by(DoctorProfile.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_doctors(
        self,
        *,
        specialization: Optional[Specialization] = None,
        branch_id: Optional[UUID] = None,
        is_available: Optional[bool] = None,
    ) -> int:
        """Count doctors matching filters."""
        query = select(func.count(DoctorProfile.id)).join(User)

        conditions = [User.is_active == True]

        if specialization:
            conditions.append(DoctorProfile.specialization == specialization)

        if is_available is not None:
            conditions.append(DoctorProfile.is_available == is_available)

        if branch_id:
            query = query.join(
                DoctorBranchAssignment,
                DoctorProfile.id == DoctorBranchAssignment.doctor_id,
            ).where(DoctorBranchAssignment.branch_id == branch_id)

        query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_by_specialization(
        self,
        specialization: Specialization,
        *,
        branch_id: Optional[UUID] = None,
        available_only: bool = True,
    ) -> Sequence[DoctorProfile]:
        """Get doctors by specialization."""
        query = (
            select(DoctorProfile)
            .where(DoctorProfile.specialization == specialization)
            .join(User)
            .where(User.is_active == True)
            .options(joinedload(DoctorProfile.user))
        )

        if available_only:
            query = query.where(DoctorProfile.is_available == True)

        if branch_id:
            query = query.join(
                DoctorBranchAssignment,
                DoctorProfile.id == DoctorBranchAssignment.doctor_id,
            ).where(DoctorBranchAssignment.branch_id == branch_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    # Branch Assignments
    async def get_branch_assignments(
        self,
        doctor_id: UUID,
    ) -> Sequence[DoctorBranchAssignment]:
        """Get all branch assignments for a doctor."""
        query = select(DoctorBranchAssignment).where(
            DoctorBranchAssignment.doctor_id == doctor_id
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def assign_to_branch(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        is_primary: bool = False,
    ) -> DoctorBranchAssignment:
        """Assign doctor to a branch."""
        assignment = DoctorBranchAssignment(
            doctor_id=doctor_id,
            branch_id=branch_id,
            is_primary=is_primary,
        )
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def remove_from_branch(
        self,
        doctor_id: UUID,
        branch_id: UUID,
    ) -> bool:
        """Remove doctor from a branch."""
        query = select(DoctorBranchAssignment).where(
            and_(
                DoctorBranchAssignment.doctor_id == doctor_id,
                DoctorBranchAssignment.branch_id == branch_id,
            )
        )
        result = await self.db.execute(query)
        assignment = result.scalar_one_or_none()

        if assignment:
            await self.db.delete(assignment)
            await self.db.flush()
            return True
        return False

    # Weekly Schedule
    async def get_weekly_schedule(
        self,
        doctor_id: UUID,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[DoctorWeeklySchedule]:
        """Get weekly schedule for a doctor."""
        query = select(DoctorWeeklySchedule).where(
            and_(
                DoctorWeeklySchedule.doctor_id == doctor_id,
                DoctorWeeklySchedule.is_active == True,
            )
        )

        if branch_id:
            query = query.where(DoctorWeeklySchedule.branch_id == branch_id)

        query = query.order_by(DoctorWeeklySchedule.day_of_week)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_schedule(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        slot_duration_minutes: int = 30,
        max_patients_per_slot: int = 1,
    ) -> DoctorWeeklySchedule:
        """Create a weekly schedule entry."""
        schedule = DoctorWeeklySchedule(
            doctor_id=doctor_id,
            branch_id=branch_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=slot_duration_minutes,
            max_patients_per_slot=max_patients_per_slot,
        )
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    # Schedule Override
    async def get_schedule_overrides(
        self,
        doctor_id: UUID,
        start_date: date,
        end_date: date,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[DoctorScheduleOverride]:
        """Get schedule overrides for a date range."""
        query = select(DoctorScheduleOverride).where(
            and_(
                DoctorScheduleOverride.doctor_id == doctor_id,
                DoctorScheduleOverride.override_date >= start_date,
                DoctorScheduleOverride.override_date <= end_date,
            )
        )

        if branch_id:
            query = query.where(DoctorScheduleOverride.branch_id == branch_id)

        query = query.order_by(DoctorScheduleOverride.override_date)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_schedule_override(
        self,
        doctor_id: UUID,
        override_date: date,
        is_available: bool = False,
        branch_id: Optional[UUID] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        reason: Optional[str] = None,
    ) -> DoctorScheduleOverride:
        """Create a schedule override (e.g., day off, special hours)."""
        override = DoctorScheduleOverride(
            doctor_id=doctor_id,
            branch_id=branch_id,
            override_date=override_date,
            is_available=is_available,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
        )
        self.db.add(override)
        await self.db.flush()
        await self.db.refresh(override)
        return override

    async def get_doctor_stats(self) -> dict[str, Any]:
        """Get doctor statistics."""
        # Total doctors
        total_query = select(func.count(DoctorProfile.id))
        total = await self.db.execute(total_query)

        # Available doctors
        available_query = select(func.count(DoctorProfile.id)).where(
            DoctorProfile.is_available == True
        )
        available = await self.db.execute(available_query)

        # By specialization
        spec_query = (
            select(DoctorProfile.specialization, func.count(DoctorProfile.id))
            .group_by(DoctorProfile.specialization)
        )
        spec_result = await self.db.execute(spec_query)
        by_specialization = {str(s.value): c for s, c in spec_result.all()}

        return {
            "total_doctors": total.scalar() or 0,
            "available_doctors": available.scalar() or 0,
            "by_specialization": by_specialization,
        }
