"""
Patient management endpoints.
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
from app.api.v1.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientListResponse,
    PatientDetailResponse,
    PatientFilter,
    PatientMedicalSummary,
    EmergencyContactUpdate,
    InsuranceInfoUpdate,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.patient import PatientService
from app.models.user import User
from app.models.enums import UserRole, Gender, BloodGroup

router = APIRouter(prefix="/patients", tags=["Patients"])


def check_patient_access(current_user: User, patient_user_id: UUID) -> bool:
    """Check if current user can access patient data."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.PATIENT and current_user.id == patient_user_id:
        return True
    if current_user.role in [UserRole.DOCTOR, UserRole.STAFF]:
        # Doctors and staff can access through appointments/records
        return True
    return False


@router.get("", response_model=PatientListResponse)
@require_permissions(Permission.VIEW_PATIENT)
async def list_patients(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    gender: Optional[Gender] = None,
    blood_group: Optional[BloodGroup] = None,
    is_active: Optional[bool] = None,
):
    """
    List all patients with filtering and pagination.

    Requires: VIEW_PATIENT permission
    """
    patient_service = PatientService(db)

    filters = PatientFilter(
        search=search,
        gender=gender,
        blood_group=blood_group,
        is_active=is_active,
    )

    patients = await patient_service.get_patients(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await patient_service.count_patients(filters=filters)

    return PatientListResponse(
        items=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=PatientDetailResponse)
async def get_my_patient_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's patient profile.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    patient_service = PatientService(db)

    try:
        patient = await patient_service.get_patient_by_user_id(current_user.id)
        return PatientDetailResponse.model_validate(patient)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )


@router.get("/me/medical-summary", response_model=PatientMedicalSummary)
async def get_my_medical_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's medical summary.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    patient_service = PatientService(db)

    try:
        patient = await patient_service.get_patient_by_user_id(current_user.id)
        summary = await patient_service.get_medical_summary(patient.id)
        return summary
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )


@router.get("/{patient_id}", response_model=PatientDetailResponse)
@require_permissions(Permission.VIEW_PATIENT)
async def get_patient(
    patient_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific patient by ID.

    Requires: VIEW_PATIENT permission
    """
    patient_service = PatientService(db)

    try:
        patient = await patient_service.get_patient(patient_id)
        return PatientDetailResponse.model_validate(patient)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )


@router.get("/{patient_id}/medical-summary", response_model=PatientMedicalSummary)
@require_permissions(Permission.VIEW_PATIENT, Permission.VIEW_MEDICAL_RECORD)
async def get_patient_medical_summary(
    patient_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get patient's medical summary including diagnoses, allergies, and recent visits.

    Requires: VIEW_PATIENT, VIEW_MEDICAL_RECORD permissions
    """
    patient_service = PatientService(db)

    try:
        summary = await patient_service.get_medical_summary(patient_id)
        return summary
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_PATIENT)
async def create_patient(
    patient_data: PatientCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new patient.

    Requires: CREATE_PATIENT permission
    """
    patient_service = PatientService(db)

    try:
        patient = await patient_service.create_patient(
            created_by=current_user.id,
            **patient_data.model_dump(),
        )
        return PatientResponse.model_validate(patient)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{patient_id}", response_model=PatientResponse)
@require_permissions(Permission.UPDATE_PATIENT)
async def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a patient.

    Requires: UPDATE_PATIENT permission
    """
    patient_service = PatientService(db)

    try:
        patient = await patient_service.update_patient(
            patient_id=patient_id,
            **patient_data.model_dump(exclude_unset=True),
        )
        return PatientResponse.model_validate(patient)
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


@router.put("/me", response_model=PatientResponse)
async def update_my_patient_profile(
    patient_data: PatientUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update current user's patient profile.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    patient_service = PatientService(db)

    try:
        patient = await patient_service.get_patient_by_user_id(current_user.id)
        updated_patient = await patient_service.update_patient(
            patient_id=patient.id,
            **patient_data.model_dump(exclude_unset=True),
        )
        return PatientResponse.model_validate(updated_patient)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )


@router.put("/{patient_id}/emergency-contact", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_PATIENT)
async def update_emergency_contact(
    patient_id: UUID,
    contact_data: EmergencyContactUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update patient's emergency contact information.

    Requires: UPDATE_PATIENT permission
    """
    patient_service = PatientService(db)

    try:
        await patient_service.update_emergency_contact(
            patient_id=patient_id,
            **contact_data.model_dump(exclude_unset=True),
        )
        return SuccessResponse(message="Emergency contact updated successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )


@router.put("/me/emergency-contact", response_model=SuccessResponse)
async def update_my_emergency_contact(
    contact_data: EmergencyContactUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update current user's emergency contact.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    patient_service = PatientService(db)

    try:
        patient = await patient_service.get_patient_by_user_id(current_user.id)
        await patient_service.update_emergency_contact(
            patient_id=patient.id,
            **contact_data.model_dump(exclude_unset=True),
        )
        return SuccessResponse(message="Emergency contact updated successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )


@router.put("/{patient_id}/insurance", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_PATIENT)
async def update_insurance_info(
    patient_id: UUID,
    insurance_data: InsuranceInfoUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update patient's insurance information.

    Requires: UPDATE_PATIENT permission
    """
    patient_service = PatientService(db)

    try:
        await patient_service.update_patient(
            patient_id=patient_id,
            insurance_provider=insurance_data.insurance_provider,
            insurance_policy_number=insurance_data.insurance_policy_number,
        )
        return SuccessResponse(message="Insurance information updated successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )


@router.delete("/{patient_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_PATIENT)
async def delete_patient(
    patient_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete (deactivate) a patient.

    Requires: DELETE_PATIENT permission
    """
    patient_service = PatientService(db)

    try:
        await patient_service.delete_patient(patient_id)
        return SuccessResponse(message="Patient deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
