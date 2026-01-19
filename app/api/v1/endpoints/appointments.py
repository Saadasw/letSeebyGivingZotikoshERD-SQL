"""
Appointment management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.api.v1.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentListResponse,
    AppointmentDetailResponse,
    AppointmentFilter,
    AppointmentReschedule,
    AppointmentCheckIn,
    AppointmentCheckOut,
    TimeSlotResponse,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.appointment import AppointmentService
from app.models.user import User
from app.models.enums import UserRole, AppointmentStatus, AppointmentType

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("", response_model=AppointmentListResponse)
@require_permissions(Permission.VIEW_APPOINTMENT)
async def list_appointments(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[AppointmentStatus] = None,
    appointment_type: Optional[AppointmentType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List appointments with filtering and pagination.

    Requires: VIEW_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    filters = AppointmentFilter(
        patient_id=patient_id,
        doctor_id=doctor_id,
        branch_id=branch_id,
        status=status,
        appointment_type=appointment_type,
        date_from=date_from,
        date_to=date_to,
    )

    appointments = await appointment_service.get_appointments(
        skip=skip,
        limit=limit,
        filters=filters,
        current_user=current_user,
    )

    total = await appointment_service.count_appointments(
        filters=filters,
        current_user=current_user,
    )

    return AppointmentListResponse(
        items=[AppointmentResponse.model_validate(a) for a in appointments],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=AppointmentListResponse)
async def get_my_appointments(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[AppointmentStatus] = None,
    upcoming_only: bool = False,
):
    """
    Get current user's appointments.

    For patients: returns their appointments.
    For doctors: returns appointments assigned to them.
    """
    appointment_service = AppointmentService(db)

    filters = AppointmentFilter(status=status)
    if upcoming_only:
        filters.date_from = date.today()

    appointments = await appointment_service.get_my_appointments(
        user=current_user,
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await appointment_service.count_my_appointments(
        user=current_user,
        filters=filters,
    )

    return AppointmentListResponse(
        items=[AppointmentResponse.model_validate(a) for a in appointments],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/slots", response_model=list[TimeSlotResponse])
async def get_available_slots(
    doctor_id: UUID,
    appointment_date: date,
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
    appointment_type: AppointmentType = AppointmentType.CONSULTATION,
):
    """
    Get available time slots for a doctor on a specific date.

    Public endpoint for booking.
    """
    appointment_service = AppointmentService(db)

    try:
        slots = await appointment_service.get_available_slots(
            doctor_id=doctor_id,
            date=appointment_date,
            branch_id=branch_id,
            appointment_type=appointment_type,
        )
        return [TimeSlotResponse.model_validate(s) for s in slots]
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )


@router.get("/{appointment_id}", response_model=AppointmentDetailResponse)
@require_permissions(Permission.VIEW_APPOINTMENT)
async def get_appointment(
    appointment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific appointment by ID.

    Requires: VIEW_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        appointment = await appointment_service.get_appointment(
            appointment_id=appointment_id,
            current_user=current_user,
        )
        return AppointmentDetailResponse.model_validate(appointment)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_APPOINTMENT)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new appointment.

    Requires: CREATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        appointment = await appointment_service.create_appointment(
            created_by=current_user.id,
            current_user=current_user,
            **appointment_data.model_dump(),
        )
        return AppointmentResponse.model_validate(appointment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    appointment_data: AppointmentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Book an appointment (patient self-booking).

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments through this endpoint",
        )

    appointment_service = AppointmentService(db)

    try:
        appointment = await appointment_service.book_appointment(
            user=current_user,
            **appointment_data.model_dump(),
        )
        return AppointmentResponse.model_validate(appointment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.put("/{appointment_id}", response_model=AppointmentResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def update_appointment(
    appointment_id: UUID,
    appointment_data: AppointmentUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an appointment.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        appointment = await appointment_service.update_appointment(
            appointment_id=appointment_id,
            current_user=current_user,
            **appointment_data.model_dump(exclude_unset=True),
        )
        return AppointmentResponse.model_validate(appointment)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def reschedule_appointment(
    appointment_id: UUID,
    reschedule_data: AppointmentReschedule,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Reschedule an appointment.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        appointment = await appointment_service.reschedule_appointment(
            appointment_id=appointment_id,
            new_date=reschedule_data.new_date,
            new_time=reschedule_data.new_time,
            reason=reschedule_data.reason,
            current_user=current_user,
        )
        return AppointmentResponse.model_validate(appointment)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/{appointment_id}/cancel", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def cancel_appointment(
    appointment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    reason: Optional[str] = None,
):
    """
    Cancel an appointment.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        await appointment_service.cancel_appointment(
            appointment_id=appointment_id,
            reason=reason,
            current_user=current_user,
        )
        return SuccessResponse(message="Appointment cancelled successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{appointment_id}/confirm", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def confirm_appointment(
    appointment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Confirm an appointment.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        await appointment_service.confirm_appointment(
            appointment_id=appointment_id,
            current_user=current_user,
        )
        return SuccessResponse(message="Appointment confirmed successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{appointment_id}/check-in", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def check_in_appointment(
    appointment_id: UUID,
    check_in_data: AppointmentCheckIn,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Check in a patient for an appointment.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        await appointment_service.check_in(
            appointment_id=appointment_id,
            room_id=check_in_data.room_id,
            notes=check_in_data.notes,
            current_user=current_user,
        )
        return SuccessResponse(message="Patient checked in successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{appointment_id}/check-out", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def check_out_appointment(
    appointment_id: UUID,
    check_out_data: AppointmentCheckOut,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Check out a patient from an appointment.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        await appointment_service.check_out(
            appointment_id=appointment_id,
            notes=check_out_data.notes,
            follow_up_required=check_out_data.follow_up_required,
            follow_up_date=check_out_data.follow_up_date,
            current_user=current_user,
        )
        return SuccessResponse(message="Patient checked out successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{appointment_id}/no-show", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_APPOINTMENT)
async def mark_no_show(
    appointment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark an appointment as no-show.

    Requires: UPDATE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        await appointment_service.mark_no_show(
            appointment_id=appointment_id,
            current_user=current_user,
        )
        return SuccessResponse(message="Appointment marked as no-show")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{appointment_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_APPOINTMENT)
async def delete_appointment(
    appointment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an appointment.

    Requires: DELETE_APPOINTMENT permission
    """
    appointment_service = AppointmentService(db)

    try:
        await appointment_service.delete_appointment(appointment_id)
        return SuccessResponse(message="Appointment deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
