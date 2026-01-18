"""Appointment repository."""

from datetime import date, time, datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.enums import AppointmentStatus, AppointmentType
from app.db.models.appointment import Appointment, TimeSlot
from app.db.models.patient import PatientProfile
from app.db.models.doctor import DoctorProfile
from app.db.models.user import User
from .base import BaseRepository


class TimeSlotRepository(BaseRepository[TimeSlot]):
    """Repository for TimeSlot model."""

    def __init__(self, db: AsyncSession):
        super().__init__(TimeSlot, db)

    async def get_available_slots(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        slot_date: date,
    ) -> Sequence[TimeSlot]:
        """Get available time slots for a doctor on a date."""
        query = (
            select(TimeSlot)
            .where(
                and_(
                    TimeSlot.doctor_id == doctor_id,
                    TimeSlot.branch_id == branch_id,
                    TimeSlot.slot_date == slot_date,
                    TimeSlot.is_available == True,
                    TimeSlot.current_bookings < TimeSlot.max_bookings,
                )
            )
            .order_by(TimeSlot.start_time)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_slots_by_date_range(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Sequence[TimeSlot]:
        """Get time slots for a date range."""
        query = (
            select(TimeSlot)
            .where(
                and_(
                    TimeSlot.doctor_id == doctor_id,
                    TimeSlot.branch_id == branch_id,
                    TimeSlot.slot_date >= start_date,
                    TimeSlot.slot_date <= end_date,
                )
            )
            .order_by(TimeSlot.slot_date, TimeSlot.start_time)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def increment_booking(self, slot_id: UUID) -> bool:
        """Increment booking count for a slot."""
        result = await self.db.execute(
            update(TimeSlot)
            .where(
                and_(
                    TimeSlot.id == slot_id,
                    TimeSlot.current_bookings < TimeSlot.max_bookings,
                )
            )
            .values(current_bookings=TimeSlot.current_bookings + 1)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def decrement_booking(self, slot_id: UUID) -> bool:
        """Decrement booking count for a slot."""
        result = await self.db.execute(
            update(TimeSlot)
            .where(
                and_(
                    TimeSlot.id == slot_id,
                    TimeSlot.current_bookings > 0,
                )
            )
            .values(current_bookings=TimeSlot.current_bookings - 1)
        )
        await self.db.flush()
        return result.rowcount > 0


class AppointmentRepository(BaseRepository[Appointment]):
    """Repository for Appointment model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Appointment, db)

    async def get_by_appointment_id(self, appointment_id: str) -> Optional[Appointment]:
        """Get appointment by auto-generated ID."""
        query = select(Appointment).where(Appointment.appointment_id == appointment_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: UUID) -> Optional[Appointment]:
        """Get appointment with related details."""
        query = (
            select(Appointment)
            .where(Appointment.id == id)
            .options(
                joinedload(Appointment.patient).joinedload(PatientProfile.user),
                joinedload(Appointment.doctor).joinedload(DoctorProfile.user),
                joinedload(Appointment.branch),
                joinedload(Appointment.time_slot),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_appointments_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[AppointmentStatus] = None,
        appointment_type: Optional[AppointmentType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
    ) -> Sequence[Appointment]:
        """Get list of appointments with filters."""
        query = (
            select(Appointment)
            .options(
                joinedload(Appointment.patient).joinedload(PatientProfile.user),
                joinedload(Appointment.doctor).joinedload(DoctorProfile.user),
                joinedload(Appointment.branch),
            )
        )

        conditions = []

        if patient_id:
            conditions.append(Appointment.patient_id == patient_id)

        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)

        if branch_id:
            conditions.append(Appointment.branch_id == branch_id)

        if status:
            conditions.append(Appointment.status == status)

        if appointment_type:
            conditions.append(Appointment.appointment_type == appointment_type)

        if date_from:
            conditions.append(Appointment.scheduled_date >= date_from)

        if date_to:
            conditions.append(Appointment.scheduled_date <= date_to)

        if search:
            # Join with patient and doctor to search names
            query = query.join(
                PatientProfile, Appointment.patient_id == PatientProfile.id
            ).join(
                User, PatientProfile.user_id == User.id
            )
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    Appointment.appointment_id.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(
            Appointment.scheduled_date.desc(),
            Appointment.scheduled_time.desc(),
        )
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_appointments(
        self,
        *,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[AppointmentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> int:
        """Count appointments matching filters."""
        query = select(func.count(Appointment.id))

        conditions = []

        if patient_id:
            conditions.append(Appointment.patient_id == patient_id)
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        if branch_id:
            conditions.append(Appointment.branch_id == branch_id)
        if status:
            conditions.append(Appointment.status == status)
        if date_from:
            conditions.append(Appointment.scheduled_date >= date_from)
        if date_to:
            conditions.append(Appointment.scheduled_date <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_patient_appointments(
        self,
        patient_id: UUID,
        *,
        status: Optional[AppointmentStatus] = None,
        upcoming_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Appointment]:
        """Get appointments for a patient."""
        query = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .options(
                joinedload(Appointment.doctor).joinedload(DoctorProfile.user),
                joinedload(Appointment.branch),
            )
        )

        if status:
            query = query.where(Appointment.status == status)

        if upcoming_only:
            today = date.today()
            query = query.where(
                and_(
                    Appointment.scheduled_date >= today,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED,
                    ]),
                )
            )

        query = query.order_by(
            Appointment.scheduled_date,
            Appointment.scheduled_time,
        ).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_doctor_appointments(
        self,
        doctor_id: UUID,
        target_date: date,
        *,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[Appointment]:
        """Get appointments for a doctor on a specific date."""
        query = (
            select(Appointment)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.scheduled_date == target_date,
                )
            )
            .options(
                joinedload(Appointment.patient).joinedload(PatientProfile.user),
                joinedload(Appointment.branch),
            )
        )

        if branch_id:
            query = query.where(Appointment.branch_id == branch_id)

        query = query.order_by(Appointment.scheduled_time)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        appointment_id: UUID,
        status: AppointmentStatus,
        **kwargs,
    ) -> Optional[Appointment]:
        """Update appointment status."""
        update_data = {"status": status, **kwargs}

        if status == AppointmentStatus.CHECKED_IN:
            update_data["check_in_time"] = datetime.utcnow()
        elif status == AppointmentStatus.COMPLETED:
            update_data["check_out_time"] = datetime.utcnow()

        return await self.update(appointment_id, update_data)

    async def get_appointment_stats(
        self,
        *,
        branch_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        """Get appointment statistics."""
        base_conditions = []

        if branch_id:
            base_conditions.append(Appointment.branch_id == branch_id)
        if doctor_id:
            base_conditions.append(Appointment.doctor_id == doctor_id)
        if date_from:
            base_conditions.append(Appointment.scheduled_date >= date_from)
        if date_to:
            base_conditions.append(Appointment.scheduled_date <= date_to)

        # Total
        total_query = select(func.count(Appointment.id))
        if base_conditions:
            total_query = total_query.where(and_(*base_conditions))
        total = await self.db.execute(total_query)

        # By status
        status_query = (
            select(Appointment.status, func.count(Appointment.id))
            .group_by(Appointment.status)
        )
        if base_conditions:
            status_query = status_query.where(and_(*base_conditions))
        status_result = await self.db.execute(status_query)
        by_status = {str(s.value): c for s, c in status_result.all()}

        # By type
        type_query = (
            select(Appointment.appointment_type, func.count(Appointment.id))
            .group_by(Appointment.appointment_type)
        )
        if base_conditions:
            type_query = type_query.where(and_(*base_conditions))
        type_result = await self.db.execute(type_query)
        by_type = {str(t.value): c for t, c in type_result.all()}

        return {
            "total_appointments": total.scalar() or 0,
            "scheduled": by_status.get("scheduled", 0),
            "confirmed": by_status.get("confirmed", 0),
            "completed": by_status.get("completed", 0),
            "cancelled": by_status.get("cancelled", 0),
            "no_show": by_status.get("no_show", 0),
            "by_type": by_type,
            "by_status": by_status,
        }
