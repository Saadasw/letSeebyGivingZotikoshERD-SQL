"""
Medical records management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError, PermissionDeniedError
from app.api.v1.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
    MedicalRecordListResponse,
    MedicalRecordDetailResponse,
    MedicalRecordFilter,
    VitalsCreate,
    VitalsResponse,
    MedicalHistoryCreate,
    MedicalHistoryResponse,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.medical_record import MedicalRecordService
from app.models.user import User
from app.models.enums import UserRole, RecordType

router = APIRouter(prefix="/medical-records", tags=["Medical Records"])


@router.get("", response_model=MedicalRecordListResponse)
@require_permissions(Permission.VIEW_MEDICAL_RECORD)
async def list_medical_records(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    appointment_id: Optional[UUID] = None,
    record_type: Optional[RecordType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List medical records with filtering and pagination.

    Requires: VIEW_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    filters = MedicalRecordFilter(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        record_type=record_type,
        date_from=date_from,
        date_to=date_to,
    )

    records = await record_service.get_medical_records(
        skip=skip,
        limit=limit,
        filters=filters,
        current_user=current_user,
    )

    total = await record_service.count_medical_records(
        filters=filters,
        current_user=current_user,
    )

    return MedicalRecordListResponse(
        items=[MedicalRecordResponse.model_validate(r) for r in records],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=MedicalRecordListResponse)
async def get_my_medical_records(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    record_type: Optional[RecordType] = None,
):
    """
    Get current user's medical records.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    record_service = MedicalRecordService(db)

    records = await record_service.get_patient_records(
        user=current_user,
        skip=skip,
        limit=limit,
        record_type=record_type,
    )

    total = await record_service.count_patient_records(
        user=current_user,
        record_type=record_type,
    )

    return MedicalRecordListResponse(
        items=[MedicalRecordResponse.model_validate(r) for r in records],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/{record_id}", response_model=MedicalRecordDetailResponse)
@require_permissions(Permission.VIEW_MEDICAL_RECORD)
async def get_medical_record(
    record_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific medical record by ID.

    Requires: VIEW_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        record = await record_service.get_medical_record(
            record_id=record_id,
            current_user=current_user,
        )
        return MedicalRecordDetailResponse.model_validate(record)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this record",
        )


@router.get("/{record_id}/history")
@require_permissions(Permission.VIEW_MEDICAL_RECORD)
async def get_medical_record_history(
    record_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get version history of a medical record.

    Requires: VIEW_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        history = await record_service.get_record_history(
            record_id=record_id,
            current_user=current_user,
        )
        return {"history": history}
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_MEDICAL_RECORD)
async def create_medical_record(
    record_data: MedicalRecordCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new medical record.

    Requires: CREATE_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        record = await record_service.create_medical_record(
            created_by=current_user.id,
            current_user=current_user,
            **record_data.model_dump(),
        )
        return MedicalRecordResponse.model_validate(record)
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


@router.put("/{record_id}", response_model=MedicalRecordResponse)
@require_permissions(Permission.UPDATE_MEDICAL_RECORD)
async def update_medical_record(
    record_id: UUID,
    record_data: MedicalRecordUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a medical record.

    Requires: UPDATE_MEDICAL_RECORD permission
    Creates a new version in history.
    """
    record_service = MedicalRecordService(db)

    try:
        record = await record_service.update_medical_record(
            record_id=record_id,
            updated_by=current_user.id,
            current_user=current_user,
            **record_data.model_dump(exclude_unset=True),
        )
        return MedicalRecordResponse.model_validate(record)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this record",
        )


@router.delete("/{record_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_MEDICAL_RECORD)
async def delete_medical_record(
    record_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a medical record.

    Requires: DELETE_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        await record_service.delete_medical_record(record_id)
        return SuccessResponse(message="Medical record deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )


# Vitals endpoints
@router.get("/patient/{patient_id}/vitals", response_model=list[VitalsResponse])
@require_permissions(Permission.VIEW_MEDICAL_RECORD)
async def get_patient_vitals(
    patient_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    Get vitals history for a patient.

    Requires: VIEW_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        vitals = await record_service.get_patient_vitals(
            patient_id=patient_id,
            skip=skip,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
        return [VitalsResponse.model_validate(v) for v in vitals]
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )


@router.post("/patient/{patient_id}/vitals", response_model=VitalsResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_MEDICAL_RECORD)
async def create_vitals(
    patient_id: UUID,
    vitals_data: VitalsCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Record vitals for a patient.

    Requires: CREATE_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        vitals = await record_service.create_vitals(
            patient_id=patient_id,
            recorded_by=current_user.id,
            **vitals_data.model_dump(),
        )
        return VitalsResponse.model_validate(vitals)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me/vitals", response_model=list[VitalsResponse])
async def get_my_vitals(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get current user's vitals history.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    record_service = MedicalRecordService(db)

    vitals = await record_service.get_my_vitals(
        user=current_user,
        skip=skip,
        limit=limit,
    )
    return [VitalsResponse.model_validate(v) for v in vitals]


# Medical history endpoints
@router.get("/patient/{patient_id}/history", response_model=list[MedicalHistoryResponse])
@require_permissions(Permission.VIEW_MEDICAL_RECORD)
async def get_patient_medical_history(
    patient_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get medical history for a patient.

    Requires: VIEW_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        history = await record_service.get_patient_medical_history(patient_id)
        return [MedicalHistoryResponse.model_validate(h) for h in history]
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )


@router.post("/patient/{patient_id}/history", response_model=MedicalHistoryResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_MEDICAL_RECORD)
async def add_medical_history(
    patient_id: UUID,
    history_data: MedicalHistoryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add medical history entry for a patient.

    Requires: CREATE_MEDICAL_RECORD permission
    """
    record_service = MedicalRecordService(db)

    try:
        history = await record_service.add_medical_history(
            patient_id=patient_id,
            recorded_by=current_user.id,
            **history_data.model_dump(),
        )
        return MedicalHistoryResponse.model_validate(history)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me/history", response_model=list[MedicalHistoryResponse])
async def get_my_medical_history(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's medical history.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    record_service = MedicalRecordService(db)

    history = await record_service.get_my_medical_history(current_user)
    return [MedicalHistoryResponse.model_validate(h) for h in history]
