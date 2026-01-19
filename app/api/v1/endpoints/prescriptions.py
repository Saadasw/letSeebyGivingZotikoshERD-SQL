"""
Prescription management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionUpdate,
    PrescriptionResponse,
    PrescriptionListResponse,
    PrescriptionDetailResponse,
    PrescriptionFilter,
    PrescriptionItemCreate,
    DispenseRequest,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.prescription import PrescriptionService
from app.models.user import User
from app.models.enums import UserRole, PrescriptionStatus

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.get("", response_model=PrescriptionListResponse)
@require_permissions(Permission.VIEW_PRESCRIPTION)
async def list_prescriptions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    status: Optional[PrescriptionStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List prescriptions with filtering and pagination.

    Requires: VIEW_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    filters = PrescriptionFilter(
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    prescriptions = await prescription_service.get_prescriptions(
        skip=skip,
        limit=limit,
        filters=filters,
        current_user=current_user,
    )

    total = await prescription_service.count_prescriptions(
        filters=filters,
        current_user=current_user,
    )

    return PrescriptionListResponse(
        items=[PrescriptionResponse.model_validate(p) for p in prescriptions],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=PrescriptionListResponse)
async def get_my_prescriptions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[PrescriptionStatus] = None,
    active_only: bool = False,
):
    """
    Get current user's prescriptions.

    For patients: returns their prescriptions.
    For doctors: returns prescriptions they created.
    """
    prescription_service = PrescriptionService(db)

    filters = PrescriptionFilter(status=status)

    prescriptions = await prescription_service.get_my_prescriptions(
        user=current_user,
        skip=skip,
        limit=limit,
        filters=filters,
        active_only=active_only,
    )

    total = await prescription_service.count_my_prescriptions(
        user=current_user,
        filters=filters,
        active_only=active_only,
    )

    return PrescriptionListResponse(
        items=[PrescriptionResponse.model_validate(p) for p in prescriptions],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/pending-dispense")
@require_permissions(Permission.DISPENSE_PRESCRIPTION)
async def get_pending_dispense(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    branch_id: Optional[UUID] = None,
):
    """
    Get prescriptions pending dispensing.

    Requires: DISPENSE_PRESCRIPTION permission (Pharmacy staff)
    """
    prescription_service = PrescriptionService(db)

    prescriptions = await prescription_service.get_pending_dispense(
        skip=skip,
        limit=limit,
        branch_id=branch_id,
    )

    return {
        "items": [PrescriptionResponse.model_validate(p) for p in prescriptions],
    }


@router.get("/{prescription_id}", response_model=PrescriptionDetailResponse)
@require_permissions(Permission.VIEW_PRESCRIPTION)
async def get_prescription(
    prescription_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific prescription by ID.

    Requires: VIEW_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    try:
        prescription = await prescription_service.get_prescription(
            prescription_id=prescription_id,
            current_user=current_user,
        )
        return PrescriptionDetailResponse.model_validate(prescription)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_PRESCRIPTION)
async def create_prescription(
    prescription_data: PrescriptionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new prescription.

    Requires: CREATE_PRESCRIPTION permission (Doctors only)
    """
    prescription_service = PrescriptionService(db)

    try:
        prescription = await prescription_service.create_prescription(
            created_by=current_user.id,
            current_user=current_user,
            **prescription_data.model_dump(),
        )
        return PrescriptionResponse.model_validate(prescription)
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


@router.put("/{prescription_id}", response_model=PrescriptionResponse)
@require_permissions(Permission.UPDATE_PRESCRIPTION)
async def update_prescription(
    prescription_id: UUID,
    prescription_data: PrescriptionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a prescription.

    Requires: UPDATE_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    try:
        prescription = await prescription_service.update_prescription(
            prescription_id=prescription_id,
            current_user=current_user,
            **prescription_data.model_dump(exclude_unset=True),
        )
        return PrescriptionResponse.model_validate(prescription)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{prescription_id}/items", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_PRESCRIPTION)
async def add_prescription_item(
    prescription_id: UUID,
    item_data: PrescriptionItemCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add an item to a prescription.

    Requires: UPDATE_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    try:
        await prescription_service.add_item(
            prescription_id=prescription_id,
            current_user=current_user,
            **item_data.model_dump(),
        )
        return SuccessResponse(message="Item added to prescription")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{prescription_id}/items/{item_id}", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_PRESCRIPTION)
async def remove_prescription_item(
    prescription_id: UUID,
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove an item from a prescription.

    Requires: UPDATE_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    try:
        await prescription_service.remove_item(
            prescription_id=prescription_id,
            item_id=item_id,
            current_user=current_user,
        )
        return SuccessResponse(message="Item removed from prescription")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription or item not found",
        )


@router.post("/{prescription_id}/dispense", response_model=SuccessResponse)
@require_permissions(Permission.DISPENSE_PRESCRIPTION)
async def dispense_prescription(
    prescription_id: UUID,
    dispense_data: DispenseRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Dispense a prescription (mark as dispensed).

    Requires: DISPENSE_PRESCRIPTION permission (Pharmacy staff)
    """
    prescription_service = PrescriptionService(db)

    try:
        await prescription_service.dispense(
            prescription_id=prescription_id,
            dispensed_by=current_user.id,
            notes=dispense_data.notes,
            partial=dispense_data.partial,
            items_dispensed=dispense_data.items_dispensed,
        )
        return SuccessResponse(message="Prescription dispensed successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{prescription_id}/cancel", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_PRESCRIPTION)
async def cancel_prescription(
    prescription_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    reason: Optional[str] = None,
):
    """
    Cancel a prescription.

    Requires: UPDATE_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    try:
        await prescription_service.cancel(
            prescription_id=prescription_id,
            cancelled_by=current_user.id,
            reason=reason,
        )
        return SuccessResponse(message="Prescription cancelled successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{prescription_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_PRESCRIPTION)
async def delete_prescription(
    prescription_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a prescription.

    Requires: DELETE_PRESCRIPTION permission
    """
    prescription_service = PrescriptionService(db)

    try:
        await prescription_service.delete_prescription(prescription_id)
        return SuccessResponse(message="Prescription deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
