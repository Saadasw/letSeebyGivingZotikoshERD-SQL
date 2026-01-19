"""
Lab test management endpoints.
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
from app.api.v1.schemas.lab_test import (
    LabTestCreate,
    LabTestUpdate,
    LabTestResponse,
    LabTestListResponse,
    LabTestDetailResponse,
    LabTestFilter,
    LabTestTypeCreate,
    LabTestTypeResponse,
    SampleCollectionRequest,
    LabTestResultCreate,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.lab_test import LabTestService
from app.models.user import User
from app.models.enums import UserRole, LabTestStatus

router = APIRouter(prefix="/lab-tests", tags=["Lab Tests"])


@router.get("", response_model=LabTestListResponse)
@require_permissions(Permission.VIEW_LAB_TEST)
async def list_lab_tests(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[UUID] = None,
    doctor_id: Optional[UUID] = None,
    status: Optional[LabTestStatus] = None,
    test_type_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List lab tests with filtering and pagination.

    Requires: VIEW_LAB_TEST permission
    """
    lab_service = LabTestService(db)

    filters = LabTestFilter(
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=status,
        test_type_id=test_type_id,
        date_from=date_from,
        date_to=date_to,
    )

    tests = await lab_service.get_lab_tests(
        skip=skip,
        limit=limit,
        filters=filters,
        current_user=current_user,
    )

    total = await lab_service.count_lab_tests(
        filters=filters,
        current_user=current_user,
    )

    return LabTestListResponse(
        items=[LabTestResponse.model_validate(t) for t in tests],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=LabTestListResponse)
async def get_my_lab_tests(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[LabTestStatus] = None,
):
    """
    Get current user's lab tests.

    For patients: returns their lab tests.
    For doctors: returns lab tests they ordered.
    """
    lab_service = LabTestService(db)

    tests = await lab_service.get_my_lab_tests(
        user=current_user,
        skip=skip,
        limit=limit,
        status=status,
    )

    total = await lab_service.count_my_lab_tests(
        user=current_user,
        status=status,
    )

    return LabTestListResponse(
        items=[LabTestResponse.model_validate(t) for t in tests],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/pending-collection")
@require_permissions(Permission.COLLECT_LAB_SAMPLE)
async def get_pending_collection(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    branch_id: Optional[UUID] = None,
):
    """
    Get lab tests pending sample collection.

    Requires: COLLECT_LAB_SAMPLE permission (Lab staff)
    """
    lab_service = LabTestService(db)

    tests = await lab_service.get_pending_collection(
        skip=skip,
        limit=limit,
        branch_id=branch_id,
    )

    return {
        "items": [LabTestResponse.model_validate(t) for t in tests],
    }


@router.get("/pending-results")
@require_permissions(Permission.ENTER_LAB_RESULT)
async def get_pending_results(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    branch_id: Optional[UUID] = None,
):
    """
    Get lab tests pending results entry.

    Requires: ENTER_LAB_RESULT permission (Lab technicians)
    """
    lab_service = LabTestService(db)

    tests = await lab_service.get_pending_results(
        skip=skip,
        limit=limit,
        branch_id=branch_id,
    )

    return {
        "items": [LabTestResponse.model_validate(t) for t in tests],
    }


@router.get("/types", response_model=list[LabTestTypeResponse])
async def list_test_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = None,
    is_active: bool = True,
):
    """
    List available lab test types.

    Public endpoint.
    """
    lab_service = LabTestService(db)

    types = await lab_service.get_test_types(
        category=category,
        is_active=is_active,
    )

    return [LabTestTypeResponse.model_validate(t) for t in types]


@router.get("/types/{type_id}", response_model=LabTestTypeResponse)
async def get_test_type(
    type_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific test type.

    Public endpoint.
    """
    lab_service = LabTestService(db)

    try:
        test_type = await lab_service.get_test_type(type_id)
        return LabTestTypeResponse.model_validate(test_type)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test type not found",
        )


@router.get("/{test_id}", response_model=LabTestDetailResponse)
@require_permissions(Permission.VIEW_LAB_TEST)
async def get_lab_test(
    test_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific lab test by ID.

    Requires: VIEW_LAB_TEST permission
    """
    lab_service = LabTestService(db)

    try:
        test = await lab_service.get_lab_test(
            test_id=test_id,
            current_user=current_user,
        )
        return LabTestDetailResponse.model_validate(test)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )


@router.post("", response_model=LabTestResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.ORDER_LAB_TEST)
async def create_lab_test(
    test_data: LabTestCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Order a new lab test.

    Requires: ORDER_LAB_TEST permission (Doctors)
    """
    lab_service = LabTestService(db)

    try:
        test = await lab_service.order_lab_test(
            ordered_by=current_user.id,
            current_user=current_user,
            **test_data.model_dump(),
        )
        return LabTestResponse.model_validate(test)
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


@router.post("/types", response_model=LabTestTypeResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.MANAGE_LAB_TYPES)
async def create_test_type(
    type_data: LabTestTypeCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new lab test type.

    Requires: MANAGE_LAB_TYPES permission
    """
    lab_service = LabTestService(db)

    try:
        test_type = await lab_service.create_test_type(
            created_by=current_user.id,
            **type_data.model_dump(),
        )
        return LabTestTypeResponse.model_validate(test_type)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{test_id}", response_model=LabTestResponse)
@require_permissions(Permission.UPDATE_LAB_TEST)
async def update_lab_test(
    test_id: UUID,
    test_data: LabTestUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a lab test.

    Requires: UPDATE_LAB_TEST permission
    """
    lab_service = LabTestService(db)

    try:
        test = await lab_service.update_lab_test(
            test_id=test_id,
            current_user=current_user,
            **test_data.model_dump(exclude_unset=True),
        )
        return LabTestResponse.model_validate(test)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{test_id}/collect-sample", response_model=SuccessResponse)
@require_permissions(Permission.COLLECT_LAB_SAMPLE)
async def collect_sample(
    test_id: UUID,
    collection_data: SampleCollectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Record sample collection for a lab test.

    Requires: COLLECT_LAB_SAMPLE permission (Lab staff)
    """
    lab_service = LabTestService(db)

    try:
        await lab_service.collect_sample(
            test_id=test_id,
            collected_by=current_user.id,
            **collection_data.model_dump(),
        )
        return SuccessResponse(message="Sample collected successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{test_id}/results", response_model=SuccessResponse)
@require_permissions(Permission.ENTER_LAB_RESULT)
async def enter_results(
    test_id: UUID,
    result_data: LabTestResultCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Enter results for a lab test.

    Requires: ENTER_LAB_RESULT permission (Lab technicians)
    """
    lab_service = LabTestService(db)

    try:
        await lab_service.enter_results(
            test_id=test_id,
            entered_by=current_user.id,
            **result_data.model_dump(),
        )
        return SuccessResponse(message="Results entered successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{test_id}/verify", response_model=SuccessResponse)
@require_permissions(Permission.VERIFY_LAB_RESULT)
async def verify_results(
    test_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    notes: Optional[str] = None,
):
    """
    Verify lab test results.

    Requires: VERIFY_LAB_RESULT permission (Senior lab staff)
    """
    lab_service = LabTestService(db)

    try:
        await lab_service.verify_results(
            test_id=test_id,
            verified_by=current_user.id,
            notes=notes,
        )
        return SuccessResponse(message="Results verified successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{test_id}/cancel", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_LAB_TEST)
async def cancel_lab_test(
    test_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    reason: Optional[str] = None,
):
    """
    Cancel a lab test.

    Requires: UPDATE_LAB_TEST permission
    """
    lab_service = LabTestService(db)

    try:
        await lab_service.cancel_test(
            test_id=test_id,
            cancelled_by=current_user.id,
            reason=reason,
        )
        return SuccessResponse(message="Lab test cancelled successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{test_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_LAB_TEST)
async def delete_lab_test(
    test_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a lab test.

    Requires: DELETE_LAB_TEST permission
    """
    lab_service = LabTestService(db)

    try:
        await lab_service.delete_lab_test(test_id)
        return SuccessResponse(message="Lab test deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab test not found",
        )
