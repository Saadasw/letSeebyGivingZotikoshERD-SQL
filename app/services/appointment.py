"""Appointment service."""

from datetime import date, time, datetime
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.models.enums import AppointmentStatus, AppointmentType
from app.db.models.appointment import Appointment
from app.repositories.appointment import AppointmentRepository, TimeSlotRepository
from app.repositories.patient import PatientRepository
from app.repositories.doctor import DoctorRepository


class AppointmentService:
    """Appointment management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.appointment_repo = AppointmentRepository(db)
        self.time_slot_repo = TimeSlotRepository(db)
        self.patient_repo = PatientRepository(db)
        self.doctor_repo = DoctorRepository(db)

    async def get_appointment(self, appointment_id: UUID) -> Optional[Appointment]:
        """Get appointment by ID."""
        return await self.appointment_repo.get_with_details(appointment_id)

    async def get_appointment_by_appointment_id(
        self,
        appointment_id: str,
    ) -> Optional[Appointment]:
        """Get appointment by auto-generated ID."""
        return await self.appointment_repo.get_by_appointment_id(appointment_id)

    async def get_appointments(
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
        return await self.appointment_repo.get_appointments_list(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            branch_id=branch_id,
            status=status,
            appointment_type=appointment_type,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )

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
        return await self.appointment_repo.count_appointments(
            patient_id=patient_id,
            doctor_id=doctor_id,
            branch_id=branch_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

    async def create_appointment(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        branch_id: UUID,
        scheduled_date: date,
        scheduled_time: time,
        appointment_type: AppointmentType = AppointmentType.CONSULTATION,
        time_slot_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Appointment:
        """Create a new appointment."""
        # Validate patient exists
        patient = await self.patient_repo.get(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        # Validate doctor exists and is available
        doctor = await self.doctor_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        if not doctor.is_available:
            raise ValidationError("Doctor is not available for appointments")

        # Check for conflicting appointments
        existing = await self.appointment_repo.get_doctor_appointments(
            doctor_id, scheduled_date, branch_id=branch_id
        )

        for apt in existing:
            if apt.scheduled_time == scheduled_time and apt.status not in [
                AppointmentStatus.CANCELLED,
                AppointmentStatus.NO_SHOW,
            ]:
                raise ConflictError("Time slot is already booked")

        # Update time slot if provided
        if time_slot_id:
            slot = await self.time_slot_repo.get(time_slot_id)
            if not slot or not slot.is_available:
                raise ValidationError("Time slot is not available")

            if not await self.time_slot_repo.increment_booking(time_slot_id):
                raise ConflictError("Time slot is fully booked")

        # Create appointment
        appointment = await self.appointment_repo.create({
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "branch_id": branch_id,
            "time_slot_id": time_slot_id,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "appointment_type": appointment_type,
            "reason": reason,
            "notes": notes,
            "status": AppointmentStatus.SCHEDULED,
            "consultation_fee": doctor.consultation_fee,
        })

        await self.db.commit()
        await self.db.refresh(appointment)

        return appointment

    async def update_appointment(
        self,
        appointment_id: UUID,
        **update_data,
    ) -> Optional[Appointment]:
        """Update appointment."""
        appointment = await self.appointment_repo.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        if appointment.status in [
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
        ]:
            raise ValidationError("Cannot update completed or cancelled appointment")

        updated = await self.appointment_repo.update(appointment_id, update_data)
        await self.db.commit()

        return updated

    async def update_status(
        self,
        appointment_id: UUID,
        status: AppointmentStatus,
        cancellation_reason: Optional[str] = None,
        doctor_notes: Optional[str] = None,
    ) -> Optional[Appointment]:
        """Update appointment status."""
        appointment = await self.appointment_repo.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        # Release time slot if cancelling
        if status == AppointmentStatus.CANCELLED and appointment.time_slot_id:
            await self.time_slot_repo.decrement_booking(appointment.time_slot_id)

        updated = await self.appointment_repo.update_status(
            appointment_id,
            status,
            cancellation_reason=cancellation_reason,
            doctor_notes=doctor_notes,
        )

        await self.db.commit()
        return updated

    async def check_in(
        self,
        appointment_id: UUID,
        notes: Optional[str] = None,
    ) -> Optional[Appointment]:
        """Check in patient for appointment."""
        appointment = await self.appointment_repo.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        if appointment.status not in [
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED,
        ]:
            raise ValidationError("Cannot check in for this appointment")

        return await self.update_status(
            appointment_id,
            AppointmentStatus.CHECKED_IN,
            doctor_notes=notes,
        )

    async def check_out(
        self,
        appointment_id: UUID,
        doctor_notes: Optional[str] = None,
    ) -> Optional[Appointment]:
        """Check out patient after appointment."""
        appointment = await self.appointment_repo.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        if appointment.status != AppointmentStatus.CHECKED_IN:
            raise ValidationError("Patient must be checked in first")

        return await self.update_status(
            appointment_id,
            AppointmentStatus.COMPLETED,
            doctor_notes=doctor_notes,
        )

    async def cancel_appointment(
        self,
        appointment_id: UUID,
        reason: str,
    ) -> Optional[Appointment]:
        """Cancel appointment."""
        return await self.update_status(
            appointment_id,
            AppointmentStatus.CANCELLED,
            cancellation_reason=reason,
        )

    async def reschedule_appointment(
        self,
        appointment_id: UUID,
        new_date: date,
        new_time: time,
        new_time_slot_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> Optional[Appointment]:
        """Reschedule appointment."""
        appointment = await self.appointment_repo.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        if appointment.status in [
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
        ]:
            raise ValidationError("Cannot reschedule completed or cancelled appointment")

        # Release old time slot
        if appointment.time_slot_id:
            await self.time_slot_repo.decrement_booking(appointment.time_slot_id)

        # Book new time slot
        if new_time_slot_id:
            if not await self.time_slot_repo.increment_booking(new_time_slot_id):
                raise ConflictError("New time slot is fully booked")

        update_data = {
            "scheduled_date": new_date,
            "scheduled_time": new_time,
            "time_slot_id": new_time_slot_id,
        }

        if reason:
            update_data["notes"] = f"Rescheduled: {reason}"

        updated = await self.appointment_repo.update(appointment_id, update_data)
        await self.db.commit()

        return updated

    async def get_patient_appointments(
        self,
        patient_id: UUID,
        *,
        status: Optional[AppointmentStatus] = None,
        upcoming_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Appointment]:
        """Get appointments for a patient."""
        return await self.appointment_repo.get_patient_appointments(
            patient_id,
            status=status,
            upcoming_only=upcoming_only,
            limit=limit,
        )

    async def get_doctor_appointments(
        self,
        doctor_id: UUID,
        target_date: date,
        *,
        branch_id: Optional[UUID] = None,
    ) -> Sequence[Appointment]:
        """Get appointments for a doctor on a specific date."""
        return await self.appointment_repo.get_doctor_appointments(
            doctor_id, target_date, branch_id=branch_id
        )

    async def get_available_slots(
        self,
        doctor_id: UUID,
        branch_id: UUID,
        target_date: date,
    ):
        """Get available time slots for a doctor."""
        return await self.time_slot_repo.get_available_slots(
            doctor_id, branch_id, target_date
        )

    async def get_appointment_stats(
        self,
        *,
        branch_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        """Get appointment statistics."""
        return await self.appointment_repo.get_appointment_stats(
            branch_id=branch_id,
            doctor_id=doctor_id,
            date_from=date_from,
            date_to=date_to,
        )
