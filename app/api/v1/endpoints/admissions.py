"""
Admission management endpoints.
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
from app.api.v1.schemas.admission import (
    AdmissionCreate,
    AdmissionUpdate,
    AdmissionResponse,
    AdmissionListResponse,
    AdmissionDetailResponse,
    AdmissionFilter,
    DischargeRequest,
    TransferRequest,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.admission import AdmissionService
from app.models.user import User
from app.models.enums import UserRole, AdmissionStatus

router = APIRouter(prefix="/admissions", tags=["Admissions"])


@router.get("", response_model=AdmissionListResponse)
@require_permissions(Permission.VIEW_ADMISSION)
async def list_admissions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[AdmissionStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List admissions with filtering and pagination.

    Requires: VIEW_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    filters = AdmissionFilter(
        patient_id=patient_id,
        doctor_id=doctor_id,
        branch_id=branch_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    admissions = await admission_service.get_admissions(
        skip=skip,
        limit=limit,
        filters=filters,
        current_user=current_user,
    )

    total = await admission_service.count_admissions(
        filters=filters,
        current_user=current_user,
    )

    return AdmissionListResponse(
        items=[AdmissionResponse.model_validate(a) for a in admissions],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/active")
@require_permissions(Permission.VIEW_ADMISSION)
async def get_active_admissions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get currently active admissions.

    Requires: VIEW_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    admissions = await admission_service.get_active_admissions(
        branch_id=branch_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": [AdmissionResponse.model_validate(a) for a in admissions],
    }


@router.get("/me", response_model=AdmissionListResponse)
async def get_my_admissions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = False,
):
    """
    Get current user's admissions.

    For patients: returns their admission history.
    For doctors: returns admissions under their care.
    """
    admission_service = AdmissionService(db)

    admissions = await admission_service.get_my_admissions(
        user=current_user,
        skip=skip,
        limit=limit,
        active_only=active_only,
    )

    total = await admission_service.count_my_admissions(
        user=current_user,
        active_only=active_only,
    )

    return AdmissionListResponse(
        items=[AdmissionResponse.model_validate(a) for a in admissions],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/{admission_id}", response_model=AdmissionDetailResponse)
@require_permissions(Permission.VIEW_ADMISSION)
async def get_admission(
    admission_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific admission by ID.

    Requires: VIEW_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    try:
        admission = await admission_service.get_admission(
            admission_id=admission_id,
            current_user=current_user,
        )
        return AdmissionDetailResponse.model_validate(admission)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found",
        )


@router.post("", response_model=AdmissionResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_ADMISSION)
async def create_admission(
    admission_data: AdmissionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new admission (admit a patient).

    Requires: CREATE_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    try:
        admission = await admission_service.create_admission(
            created_by=current_user.id,
            **admission_data.model_dump(),
        )
        return AdmissionResponse.model_validate(admission)
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


@router.put("/{admission_id}", response_model=AdmissionResponse)
@require_permissions(Permission.UPDATE_ADMISSION)
async def update_admission(
    admission_id: UUID,
    admission_data: AdmissionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an admission.

    Requires: UPDATE_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    try:
        admission = await admission_service.update_admission(
            admission_id=admission_id,
            **admission_data.model_dump(exclude_unset=True),
        )
        return AdmissionResponse.model_validate(admission)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{admission_id}/discharge", response_model=SuccessResponse)
@require_permissions(Permission.DISCHARGE_PATIENT)
async def discharge_patient(
    admission_id: UUID,
    discharge_data: DischargeRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Discharge a patient.

    Requires: DISCHARGE_PATIENT permission
    """
    admission_service = AdmissionService(db)

    try:
        await admission_service.discharge(
            admission_id=admission_id,
            discharged_by=current_user.id,
            **discharge_data.model_dump(),
        )
        return SuccessResponse(message="Patient discharged successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{admission_id}/transfer", response_model=SuccessResponse)
@require_permissions(Permission.TRANSFER_PATIENT)
async def transfer_patient(
    admission_id: UUID,
    transfer_data: TransferRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Transfer a patient to different room/bed/branch.

    Requires: TRANSFER_PATIENT permission
    """
    admission_service = AdmissionService(db)

    try:
        await admission_service.transfer(
            admission_id=admission_id,
            transferred_by=current_user.id,
            **transfer_data.model_dump(),
        )
        return SuccessResponse(message="Patient transferred successfully")
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


@router.post("/{admission_id}/extend", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_ADMISSION)
async def extend_admission(
    admission_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    new_expected_discharge: date = Query(...),
    reason: Optional[str] = None,
):
    """
    Extend expected discharge date.

    Requires: UPDATE_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    try:
        await admission_service.extend(
            admission_id=admission_id,
            new_expected_discharge=new_expected_discharge,
            reason=reason,
        )
        return SuccessResponse(message="Admission extended successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{admission_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_ADMISSION)
async def delete_admission(
    admission_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an admission.

    Requires: DELETE_ADMISSION permission
    """
    admission_service = AdmissionService(db)

    try:
        await admission_service.delete_admission(admission_id)
        return SuccessResponse(message="Admission deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found",
        )
