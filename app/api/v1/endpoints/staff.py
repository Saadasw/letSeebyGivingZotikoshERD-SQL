"""
Staff management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.staff import (
    StaffCreate,
    StaffUpdate,
    StaffResponse,
    StaffListResponse,
    StaffDetailResponse,
    StaffFilter,
    StaffDepartmentTransfer,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.staff import StaffService
from app.models.user import User
from app.models.enums import UserRole, StaffDepartment

router = APIRouter(prefix="/staff", tags=["Staff"])


@router.get("", response_model=StaffListResponse)
@require_permissions(Permission.VIEW_STAFF)
async def list_staff(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    department: Optional[StaffDepartment] = None,
    branch_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
):
    """
    List all staff members with filtering and pagination.

    Requires: VIEW_STAFF permission
    """
    staff_service = StaffService(db)

    filters = StaffFilter(
        search=search,
        department=department,
        branch_id=branch_id,
        is_active=is_active,
    )

    staff_members = await staff_service.get_staff_members(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await staff_service.count_staff(filters=filters)

    return StaffListResponse(
        items=[StaffResponse.model_validate(s) for s in staff_members],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/me", response_model=StaffDetailResponse)
async def get_my_staff_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's staff profile.

    Only for staff members.
    """
    if current_user.role != UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff members can access this endpoint",
        )

    staff_service = StaffService(db)

    try:
        staff = await staff_service.get_staff_by_user_id(current_user.id)
        return StaffDetailResponse.model_validate(staff)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff profile not found",
        )


@router.get("/departments")
async def list_departments(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    List all staff departments.
    """
    departments = [
        {"value": d.value, "name": d.name.replace("_", " ").title()}
        for d in StaffDepartment
    ]
    return {"departments": departments}


@router.get("/{staff_id}", response_model=StaffDetailResponse)
@require_permissions(Permission.VIEW_STAFF)
async def get_staff(
    staff_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific staff member by ID.

    Requires: VIEW_STAFF permission
    """
    staff_service = StaffService(db)

    try:
        staff = await staff_service.get_staff(staff_id)
        return StaffDetailResponse.model_validate(staff)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_STAFF)
async def create_staff(
    staff_data: StaffCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new staff member.

    Requires: CREATE_STAFF permission
    """
    staff_service = StaffService(db)

    try:
        staff = await staff_service.create_staff(
            created_by=current_user.id,
            **staff_data.model_dump(),
        )
        return StaffResponse.model_validate(staff)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{staff_id}", response_model=StaffResponse)
@require_permissions(Permission.UPDATE_STAFF)
async def update_staff(
    staff_id: UUID,
    staff_data: StaffUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a staff member.

    Requires: UPDATE_STAFF permission
    """
    staff_service = StaffService(db)

    try:
        staff = await staff_service.update_staff(
            staff_id=staff_id,
            **staff_data.model_dump(exclude_unset=True),
        )
        return StaffResponse.model_validate(staff)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/me", response_model=StaffResponse)
async def update_my_staff_profile(
    staff_data: StaffUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update current user's staff profile.

    Only for staff members.
    """
    if current_user.role != UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff members can access this endpoint",
        )

    staff_service = StaffService(db)

    try:
        staff = await staff_service.get_staff_by_user_id(current_user.id)
        updated_staff = await staff_service.update_staff(
            staff_id=staff.id,
            **staff_data.model_dump(exclude_unset=True),
        )
        return StaffResponse.model_validate(updated_staff)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff profile not found",
        )


@router.post("/{staff_id}/transfer", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_STAFF)
async def transfer_staff_department(
    staff_id: UUID,
    transfer_data: StaffDepartmentTransfer,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Transfer a staff member to a different department.

    Requires: UPDATE_STAFF permission
    """
    staff_service = StaffService(db)

    try:
        await staff_service.transfer_department(
            staff_id=staff_id,
            new_department=transfer_data.new_department,
            new_branch_id=transfer_data.new_branch_id,
            effective_date=transfer_data.effective_date,
        )
        return SuccessResponse(message="Staff transferred successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{staff_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_STAFF)
async def delete_staff(
    staff_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete (deactivate) a staff member.

    Requires: DELETE_STAFF permission
    """
    staff_service = StaffService(db)

    try:
        await staff_service.delete_staff(staff_id)
        return SuccessResponse(message="Staff member deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )
