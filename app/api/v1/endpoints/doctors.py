"""
Doctor management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date, time
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    DoctorListResponse,
    DoctorDetailResponse,
    DoctorFilter,
    DoctorScheduleCreate,
    DoctorScheduleUpdate,
    DoctorScheduleResponse,
    DoctorAvailabilitySlot,
    DoctorBranchAssignment,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.doctor import DoctorService
from app.models.user import User
from app.models.enums import UserRole, DayOfWeek

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("", response_model=DoctorListResponse)
async def list_doctors(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    specialization: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    is_available: Optional[bool] = None,
):
    """
    List all doctors with filtering and pagination.

    Public endpoint - no authentication required.
    """
    doctor_service = DoctorService(db)

    filters = DoctorFilter(
        search=search,
        specialization=specialization,
        branch_id=branch_id,
        is_available=is_available,
    )

    doctors = await doctor_service.get_doctors(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await doctor_service.count_doctors(filters=filters)

    return DoctorListResponse(
        items=[DoctorResponse.model_validate(d) for d in doctors],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=DoctorDetailResponse)
async def get_my_doctor_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's doctor profile.

    Only for doctors.
    """
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this endpoint",
        )

    doctor_service = DoctorService(db)

    try:
        doctor = await doctor_service.get_doctor_by_user_id(current_user.id)
        return DoctorDetailResponse.model_validate(doctor)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )


@router.get("/specializations")
async def list_specializations(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    List all available doctor specializations.

    Public endpoint.
    """
    doctor_service = DoctorService(db)
    specializations = await doctor_service.get_specializations()
    return {"specializations": specializations}


@router.get("/{doctor_id}", response_model=DoctorDetailResponse)
async def get_doctor(
    doctor_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific doctor by ID.

    Public endpoint - no authentication required.
    """
    doctor_service = DoctorService(db)

    try:
        doctor = await doctor_service.get_doctor(doctor_id)
        return DoctorDetailResponse.model_validate(doctor)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )


@router.get("/{doctor_id}/availability")
async def get_doctor_availability(
    doctor_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    Get doctor's availability slots.

    Public endpoint for booking.
    """
    doctor_service = DoctorService(db)

    try:
        slots = await doctor_service.get_availability(
            doctor_id=doctor_id,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
        )
        return {"slots": [DoctorAvailabilitySlot.model_validate(s) for s in slots]}
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )


@router.get("/{doctor_id}/schedules", response_model=list[DoctorScheduleResponse])
async def get_doctor_schedules(
    doctor_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
):
    """
    Get doctor's weekly schedules.

    Public endpoint.
    """
    doctor_service = DoctorService(db)

    try:
        schedules = await doctor_service.get_schedules(
            doctor_id=doctor_id,
            branch_id=branch_id,
        )
        return [DoctorScheduleResponse.model_validate(s) for s in schedules]
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_DOCTOR)
async def create_doctor(
    doctor_data: DoctorCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new doctor.

    Requires: CREATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        doctor = await doctor_service.create_doctor(
            created_by=current_user.id,
            **doctor_data.model_dump(),
        )
        return DoctorResponse.model_validate(doctor)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{doctor_id}", response_model=DoctorResponse)
@require_permissions(Permission.UPDATE_DOCTOR)
async def update_doctor(
    doctor_id: UUID,
    doctor_data: DoctorUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a doctor.

    Requires: UPDATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        doctor = await doctor_service.update_doctor(
            doctor_id=doctor_id,
            **doctor_data.model_dump(exclude_unset=True),
        )
        return DoctorResponse.model_validate(doctor)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/me", response_model=DoctorResponse)
async def update_my_doctor_profile(
    doctor_data: DoctorUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update current user's doctor profile.

    Only for doctors.
    """
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this endpoint",
        )

    doctor_service = DoctorService(db)

    try:
        doctor = await doctor_service.get_doctor_by_user_id(current_user.id)
        updated_doctor = await doctor_service.update_doctor(
            doctor_id=doctor.id,
            **doctor_data.model_dump(exclude_unset=True),
        )
        return DoctorResponse.model_validate(updated_doctor)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )


@router.post("/{doctor_id}/schedules", response_model=DoctorScheduleResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.UPDATE_DOCTOR)
async def create_doctor_schedule(
    doctor_id: UUID,
    schedule_data: DoctorScheduleCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a schedule for a doctor.

    Requires: UPDATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        schedule = await doctor_service.create_schedule(
            doctor_id=doctor_id,
            **schedule_data.model_dump(),
        )
        return DoctorScheduleResponse.model_validate(schedule)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{doctor_id}/schedules/{schedule_id}", response_model=DoctorScheduleResponse)
@require_permissions(Permission.UPDATE_DOCTOR)
async def update_doctor_schedule(
    doctor_id: UUID,
    schedule_id: UUID,
    schedule_data: DoctorScheduleUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a doctor's schedule.

    Requires: UPDATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        schedule = await doctor_service.update_schedule(
            schedule_id=schedule_id,
            **schedule_data.model_dump(exclude_unset=True),
        )
        return DoctorScheduleResponse.model_validate(schedule)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{doctor_id}/schedules/{schedule_id}", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_DOCTOR)
async def delete_doctor_schedule(
    doctor_id: UUID,
    schedule_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a doctor's schedule.

    Requires: UPDATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        await doctor_service.delete_schedule(schedule_id)
        return SuccessResponse(message="Schedule deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )


@router.post("/{doctor_id}/branches", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_DOCTOR)
async def assign_doctor_to_branch(
    doctor_id: UUID,
    assignment: DoctorBranchAssignment,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Assign a doctor to a branch.

    Requires: UPDATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        await doctor_service.assign_to_branch(
            doctor_id=doctor_id,
            branch_id=assignment.branch_id,
            is_primary=assignment.is_primary,
        )
        return SuccessResponse(message="Doctor assigned to branch successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor or branch not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{doctor_id}/branches/{branch_id}", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_DOCTOR)
async def remove_doctor_from_branch(
    doctor_id: UUID,
    branch_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove a doctor from a branch.

    Requires: UPDATE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        await doctor_service.remove_from_branch(doctor_id, branch_id)
        return SuccessResponse(message="Doctor removed from branch successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )


@router.delete("/{doctor_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_DOCTOR)
async def delete_doctor(
    doctor_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete (deactivate) a doctor.

    Requires: DELETE_DOCTOR permission
    """
    doctor_service = DoctorService(db)

    try:
        await doctor_service.delete_doctor(doctor_id)
        return SuccessResponse(message="Doctor deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
