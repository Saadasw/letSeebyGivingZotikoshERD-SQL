"""
Branch management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    BranchListResponse,
    BranchDetailResponse,
    BranchFilter,
    BranchStats,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.branch import BranchService
from app.models.user import User

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("", response_model=BranchListResponse)
async def list_branches(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    city: Optional[str] = None,
    is_active: Optional[bool] = True,
):
    """
    List all branches with filtering and pagination.

    Public endpoint - no authentication required.
    """
    branch_service = BranchService(db)

    filters = BranchFilter(
        search=search,
        city=city,
        is_active=is_active,
    )

    branches = await branch_service.get_branches(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await branch_service.count_branches(filters=filters)

    return BranchListResponse(
        items=[BranchResponse.model_validate(b) for b in branches],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/{branch_id}", response_model=BranchDetailResponse)
async def get_branch(
    branch_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific branch by ID.

    Public endpoint - no authentication required.
    """
    branch_service = BranchService(db)

    try:
        branch = await branch_service.get_branch(branch_id)
        return BranchDetailResponse.model_validate(branch)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )


@router.get("/{branch_id}/stats", response_model=BranchStats)
@require_permissions(Permission.VIEW_BRANCH)
async def get_branch_stats(
    branch_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get statistics for a specific branch.

    Requires: VIEW_BRANCH permission
    """
    branch_service = BranchService(db)

    try:
        stats = await branch_service.get_branch_stats(branch_id)
        return stats
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )


@router.get("/{branch_id}/doctors")
async def get_branch_doctors(
    branch_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    specialization: Optional[str] = None,
):
    """
    Get all doctors at a specific branch.

    Public endpoint.
    """
    branch_service = BranchService(db)

    try:
        doctors = await branch_service.get_branch_doctors(
            branch_id=branch_id,
            skip=skip,
            limit=limit,
            specialization=specialization,
        )
        return {"doctors": doctors}
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_BRANCH)
async def create_branch(
    branch_data: BranchCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new branch.

    Requires: CREATE_BRANCH permission
    """
    branch_service = BranchService(db)

    try:
        branch = await branch_service.create_branch(
            created_by=current_user.id,
            **branch_data.model_dump(),
        )
        return BranchResponse.model_validate(branch)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{branch_id}", response_model=BranchResponse)
@require_permissions(Permission.UPDATE_BRANCH)
async def update_branch(
    branch_id: UUID,
    branch_data: BranchUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a branch.

    Requires: UPDATE_BRANCH permission
    """
    branch_service = BranchService(db)

    try:
        branch = await branch_service.update_branch(
            branch_id=branch_id,
            **branch_data.model_dump(exclude_unset=True),
        )
        return BranchResponse.model_validate(branch)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{branch_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_BRANCH)
async def delete_branch(
    branch_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete (deactivate) a branch.

    Requires: DELETE_BRANCH permission
    """
    branch_service = BranchService(db)

    try:
        await branch_service.delete_branch(branch_id)
        return SuccessResponse(message="Branch deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
