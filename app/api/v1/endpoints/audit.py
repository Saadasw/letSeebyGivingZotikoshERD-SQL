"""
Audit and system settings endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.audit import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogFilter,
    SystemSettingCreate,
    SystemSettingUpdate,
    SystemSettingResponse,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.audit import AuditService
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


# Audit Log endpoints
@router.get("/audit-logs", response_model=AuditLogListResponse)
@require_permissions(Permission.VIEW_AUDIT_LOG)
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List audit logs with filtering and pagination.

    Requires: VIEW_AUDIT_LOG permission (Admin only)
    """
    audit_service = AuditService(db)

    filters = AuditLogFilter(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
    )

    logs = await audit_service.get_audit_logs(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await audit_service.count_audit_logs(filters=filters)

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/audit-logs/user/{user_id}", response_model=AuditLogListResponse)
@require_permissions(Permission.VIEW_AUDIT_LOG)
async def get_user_audit_logs(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    Get audit logs for a specific user.

    Requires: VIEW_AUDIT_LOG permission
    """
    audit_service = AuditService(db)

    logs = await audit_service.get_user_audit_logs(
        user_id=user_id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )

    total = await audit_service.count_user_audit_logs(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/audit-logs/entity/{entity_type}/{entity_id}", response_model=AuditLogListResponse)
@require_permissions(Permission.VIEW_AUDIT_LOG)
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get audit logs for a specific entity.

    Requires: VIEW_AUDIT_LOG permission
    """
    audit_service = AuditService(db)

    logs = await audit_service.get_entity_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit,
    )

    total = await audit_service.count_entity_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
@require_permissions(Permission.VIEW_AUDIT_LOG)
async def get_audit_log(
    log_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific audit log entry.

    Requires: VIEW_AUDIT_LOG permission
    """
    audit_service = AuditService(db)

    try:
        log = await audit_service.get_audit_log(log_id)
        return AuditLogResponse.model_validate(log)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )


# System Settings endpoints
@router.get("/settings", response_model=list[SystemSettingResponse])
@require_permissions(Permission.VIEW_SYSTEM_SETTINGS)
async def list_system_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = None,
):
    """
    List system settings.

    Requires: VIEW_SYSTEM_SETTINGS permission
    """
    audit_service = AuditService(db)
    settings = await audit_service.get_settings(category=category)
    return [SystemSettingResponse.model_validate(s) for s in settings]


@router.get("/settings/{key}", response_model=SystemSettingResponse)
@require_permissions(Permission.VIEW_SYSTEM_SETTINGS)
async def get_system_setting(
    key: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific system setting.

    Requires: VIEW_SYSTEM_SETTINGS permission
    """
    audit_service = AuditService(db)

    try:
        setting = await audit_service.get_setting(key)
        return SystemSettingResponse.model_validate(setting)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )


@router.post("/settings", response_model=SystemSettingResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.MANAGE_SYSTEM_SETTINGS)
async def create_system_setting(
    setting_data: SystemSettingCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new system setting.

    Requires: MANAGE_SYSTEM_SETTINGS permission
    """
    audit_service = AuditService(db)

    try:
        setting = await audit_service.create_setting(
            created_by=current_user.id,
            **setting_data.model_dump(),
        )
        return SystemSettingResponse.model_validate(setting)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/settings/{key}", response_model=SystemSettingResponse)
@require_permissions(Permission.MANAGE_SYSTEM_SETTINGS)
async def update_system_setting(
    key: str,
    setting_data: SystemSettingUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a system setting.

    Requires: MANAGE_SYSTEM_SETTINGS permission
    """
    audit_service = AuditService(db)

    try:
        setting = await audit_service.update_setting(
            key=key,
            updated_by=current_user.id,
            **setting_data.model_dump(exclude_unset=True),
        )
        return SystemSettingResponse.model_validate(setting)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/settings/{key}", response_model=SuccessResponse)
@require_permissions(Permission.MANAGE_SYSTEM_SETTINGS)
async def delete_system_setting(
    key: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a system setting.

    Requires: MANAGE_SYSTEM_SETTINGS permission
    """
    audit_service = AuditService(db)

    try:
        await audit_service.delete_setting(key)
        return SuccessResponse(message="Setting deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )


# Dashboard/Stats endpoints
@router.get("/dashboard/stats")
@require_permissions(Permission.VIEW_DASHBOARD)
async def get_dashboard_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
):
    """
    Get dashboard statistics.

    Requires: VIEW_DASHBOARD permission
    """
    audit_service = AuditService(db)
    stats = await audit_service.get_dashboard_stats(branch_id)
    return stats


@router.get("/dashboard/activity")
@require_permissions(Permission.VIEW_DASHBOARD)
async def get_recent_activity(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=50),
):
    """
    Get recent system activity.

    Requires: VIEW_DASHBOARD permission
    """
    audit_service = AuditService(db)
    activity = await audit_service.get_recent_activity(limit)
    return {"activity": activity}
