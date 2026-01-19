"""
User management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions, check_permission
from app.core.exceptions import NotFoundError, ValidationError, PermissionDeniedError
from app.api.v1.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserDetailResponse,
    UserFilter,
    UserStats,
)
from app.api.v1.schemas.base import SuccessResponse, PaginationParams
from app.services.user import UserService
from app.models.user import User
from app.models.enums import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
@require_permissions(Permission.VIEW_USER)
async def list_users(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
):
    """
    List all users with filtering and pagination.

    Requires: VIEW_USER permission
    """
    user_service = UserService(db)

    filters = UserFilter(
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        search=search,
    )

    users = await user_service.get_users(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await user_service.count_users(filters=filters)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/stats", response_model=UserStats)
@require_permissions(Permission.VIEW_USER)
async def get_user_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get user statistics.

    Requires: VIEW_USER permission
    """
    user_service = UserService(db)
    stats = await user_service.get_user_stats()
    return stats


@router.get("/{user_id}", response_model=UserDetailResponse)
@require_permissions(Permission.VIEW_USER)
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific user by ID.

    Requires: VIEW_USER permission
    """
    user_service = UserService(db)

    try:
        user = await user_service.get_user(user_id)
        return UserDetailResponse.model_validate(user)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_USER)
async def create_user(
    user_data: UserCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new user.

    Requires: CREATE_USER permission
    """
    user_service = UserService(db)

    try:
        user = await user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            phone=user_data.phone,
            is_active=user_data.is_active,
            created_by=current_user.id,
        )
        return UserResponse.model_validate(user)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{user_id}", response_model=UserResponse)
@require_permissions(Permission.UPDATE_USER)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a user.

    Requires: UPDATE_USER permission
    """
    user_service = UserService(db)

    try:
        user = await user_service.update_user(
            user_id=user_id,
            **user_data.model_dump(exclude_unset=True),
        )
        return UserResponse.model_validate(user)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{user_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_USER)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete (deactivate) a user.

    Requires: DELETE_USER permission
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user_service = UserService(db)

    try:
        await user_service.delete_user(user_id)
        return SuccessResponse(message="User deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("/{user_id}/activate", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_USER)
async def activate_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Activate a user account.

    Requires: UPDATE_USER permission
    """
    user_service = UserService(db)

    try:
        await user_service.update_user(user_id, is_active=True)
        return SuccessResponse(message="User activated successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("/{user_id}/deactivate", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_USER)
async def deactivate_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Deactivate a user account.

    Requires: UPDATE_USER permission
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user_service = UserService(db)

    try:
        await user_service.update_user(user_id, is_active=False)
        return SuccessResponse(message="User deactivated successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("/{user_id}/verify", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_USER)
async def verify_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark a user as verified.

    Requires: UPDATE_USER permission
    """
    user_service = UserService(db)

    try:
        await user_service.update_user(user_id, is_verified=True)
        return SuccessResponse(message="User verified successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("/{user_id}/unlock", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_USER)
async def unlock_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Unlock a locked user account.

    Requires: UPDATE_USER permission
    """
    user_service = UserService(db)

    try:
        await user_service.unlock_user(user_id)
        return SuccessResponse(message="User account unlocked successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
