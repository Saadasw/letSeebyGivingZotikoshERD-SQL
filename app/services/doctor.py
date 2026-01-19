"""Doctor service."""

from datetime import date, time
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.db.models.enums import DayOfWeek, Specialization, UserRole
from app.db.models.doctor import DoctorProfile
from app.repositories.doctor import DoctorRepository
from app.repositories.user import UserRepository


class DoctorService:
    """Doctor management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doctor_repo = DoctorRepository(db)
        self.user_repo = UserRepository(db)

    async def get_doctor(self, doctor_id: UUID) -> Optional[DoctorProfile]:
        """Get doctor by ID."""
        return await self.doctor_repo.get_with_details(doctor_id)

    async def get_doctor_by_user_id(self, user_id: UUID) -> Optional[DoctorProfile]:
        """Get doctor by user ID."""
        return await self.doctor_repo.get_by_user_id(user_id)

    async def get_doctor_by_doctor_id(self, doctor_id: str) -> Optional[DoctorProfile]:
        """Get doctor by auto-generated doctor ID."""
        return await self.doctor_repo.get_by_doctor_id(doctor_id)

    async def get_doctors(
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
        return await self.doctor_repo.get_doctors_list(
            skip=skip,
            limit=limit,
            search=search,
            specialization=specialization,
            branch_id=branch_id,
            is_available=is_available,
            min_experience=min_experience,
        )

    async def count_doctors(
        self,
        *,
        specialization: Optional[Specialization] = None,
        branch_id: Optional[UUID] = None,
        is_available: Optional[bool] = None,
    ) -> int:
        """Count doctors matching filters."""
        return await self.doctor_repo.count_doctors(
            specialization=specialization,
            branch_id=branch_id,
            is_available=is_available,
        )

    async def create_doctor(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        specialization: Specialization,
        qualification: str,
        license_number: str,
        phone: Optional[str] = None,
        experience_years: int = 0,
        consultation_fee: Decimal = Decimal("0.00"),
        **doctor_data,
    ) -> DoctorProfile:
        """Create a new doctor with user account."""
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        # Create user
        user = await self.user_repo.create({
            "email": email,
            "hashed_password": get_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "role": UserRole.DOCTOR,
            "is_active": True,
            "is_verified": True,
        })

        # Create doctor profile
        doctor = await self.doctor_repo.create({
            "user_id": user.id,
            "specialization": specialization,
            "qualification": qualification,
            "license_number": license_number,
            "experience_years": experience_years,
            "consultation_fee": consultation_fee,
            **doctor_data,
        })

        await self.db.commit()
        await self.db.refresh(doctor)

        return doctor

    async def update_doctor(
        self,
        doctor_id: UUID,
        **update_data,
    ) -> Optional[DoctorProfile]:
        """Update doctor profile."""
        doctor = await self.doctor_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        updated = await self.doctor_repo.update(doctor_id, update_data)
        await self.db.commit()

        return updated

    async def set_availability(
        self,
        doctor_id: UUID,
        is_available: bool,
    ) -> Optional[DoctorProfile]:
        """Set doctor availability."""
        return await self.update_doctor(doctor_id, is_available=is_available)

    # Branch Assignments
    async def get_branch_assignments(
        self,
        doctor_id: UUID,
    ):
        """Get doctor's branch assignments."""
        return await self.doctor_repo.get_branch_assignments(doctor_id)

    async def assign_to_branch(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        is_primary: bool = False,
    ):
        """Assign doctor to a branch."""
        doctor = await self.doctor_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        assignment = await self.doctor_repo.assign_to_branch(
            doctor_id, branch_id, is_primary
        )
        await self.db.commit()

        return assignment

    async def remove_from_branch(
        self,
        doctor_id: UUID,
        branch_id: UUID,
    ) -> bool:
        """Remove doctor from a branch."""
        result = await self.doctor_repo.remove_from_branch(doctor_id, branch_id)
        if result:
            await self.db.commit()
        return result

    # Weekly Schedule
    async def get_weekly_schedule(
        self,
        doctor_id: UUID,
        branch_id: Optional[UUID] = None,
    ):
        """Get doctor's weekly schedule."""
        return await self.doctor_repo.get_weekly_schedule(doctor_id, branch_id)

    async def create_schedule(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        slot_duration_minutes: int = 30,
        max_patients_per_slot: int = 1,
    ):
        """Create a weekly schedule entry."""
        doctor = await self.doctor_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        schedule = await self.doctor_repo.create_schedule(
            doctor_id=doctor_id,
            branch_id=branch_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=slot_duration_minutes,
            max_patients_per_slot=max_patients_per_slot,
        )
        await self.db.commit()

        return schedule

    # Schedule Override
    async def get_schedule_overrides(
        self,
        doctor_id: UUID,
        start_date: date,
        end_date: date,
        branch_id: Optional[UUID] = None,
    ):
        """Get schedule overrides for a date range."""
        return await self.doctor_repo.get_schedule_overrides(
            doctor_id, start_date, end_date, branch_id
        )

    async def create_schedule_override(
        self,
        doctor_id: UUID,
        override_date: date,
        is_available: bool = False,
        branch_id: Optional[UUID] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        reason: Optional[str] = None,
    ):
        """Create a schedule override."""
        doctor = await self.doctor_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        override = await self.doctor_repo.create_schedule_override(
            doctor_id=doctor_id,
            override_date=override_date,
            is_available=is_available,
            branch_id=branch_id,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
        )
        await self.db.commit()

        return override

    async def get_doctor_availability(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        target_date: date,
    ) -> dict[str, Any]:
        """Get doctor's availability for a specific date."""
        doctor = await self.doctor_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        # Get day of week
        day_of_week = DayOfWeek(target_date.strftime("%A").lower())

        # Check for override
        overrides = await self.doctor_repo.get_schedule_overrides(
            doctor_id, target_date, target_date, branch_id
        )

        if overrides:
            override = overrides[0]
            if not override.is_available:
                return {
                    "doctor_id": doctor_id,
                    "branch_id": branch_id,
                    "date": target_date,
                    "is_working": False,
                    "slots": [],
                    "override_reason": override.reason,
                }

        # Get schedule for the day
        schedules = await self.doctor_repo.get_weekly_schedule(doctor_id, branch_id)
        day_schedule = next(
            (s for s in schedules if s.day_of_week == day_of_week and s.is_active),
            None,
        )

        if not day_schedule:
            return {
                "doctor_id": doctor_id,
                "branch_id": branch_id,
                "date": target_date,
                "is_working": False,
                "slots": [],
                "override_reason": None,
            }

        # Generate time slots
        from datetime import datetime, timedelta

        slots = []
        current = datetime.combine(target_date, day_schedule.start_time)
        end = datetime.combine(target_date, day_schedule.end_time)
        duration = timedelta(minutes=day_schedule.slot_duration_minutes)

        while current + duration <= end:
            slot_end = current + duration
            slots.append({
                "start_time": current.time(),
                "end_time": slot_end.time(),
                "is_available": True,  # Would need to check appointments
                "booked_count": 0,
                "max_capacity": day_schedule.max_patients_per_slot,
            })
            current = slot_end

        return {
            "doctor_id": doctor_id,
            "branch_id": branch_id,
            "date": target_date,
            "is_working": True,
            "slots": slots,
            "override_reason": None,
        }

    async def get_doctors_by_specialization(
        self,
        specialization: Specialization,
        *,
        branch_id: Optional[UUID] = None,
        available_only: bool = True,
    ) -> Sequence[DoctorProfile]:
        """Get doctors by specialization."""
        return await self.doctor_repo.get_by_specialization(
            specialization,
            branch_id=branch_id,
            available_only=available_only,
        )

    async def get_doctor_stats(self) -> dict[str, Any]:
        """Get doctor statistics."""
        return await self.doctor_repo.get_doctor_stats()
