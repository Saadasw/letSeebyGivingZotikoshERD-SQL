"""
Notification management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    NotificationFilter,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationTemplateResponse,
    NotificationPreferencesUpdate,
    NotificationPreferencesResponse,
    BulkNotificationRequest,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.notification import NotificationService
from app.models.user import User
from app.models.enums import NotificationType, NotificationStatus

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_my_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    notification_type: Optional[NotificationType] = None,
):
    """
    Get current user's notifications.
    """
    notification_service = NotificationService(db)

    filters = NotificationFilter(
        unread_only=unread_only,
        notification_type=notification_type,
    )

    notifications = await notification_service.get_user_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await notification_service.count_user_notifications(
        user_id=current_user.id,
        filters=filters,
    )

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get count of unread notifications.
    """
    notification_service = NotificationService(db)
    count = await notification_service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's notification preferences.
    """
    notification_service = NotificationService(db)
    preferences = await notification_service.get_preferences(current_user.id)
    return NotificationPreferencesResponse.model_validate(preferences)


@router.put("/preferences", response_model=SuccessResponse)
async def update_notification_preferences(
    preferences_data: NotificationPreferencesUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update current user's notification preferences.
    """
    notification_service = NotificationService(db)

    await notification_service.update_preferences(
        user_id=current_user.id,
        **preferences_data.model_dump(exclude_unset=True),
    )

    return SuccessResponse(message="Preferences updated successfully")


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific notification.
    """
    notification_service = NotificationService(db)

    try:
        notification = await notification_service.get_notification(
            notification_id=notification_id,
            user_id=current_user.id,
        )
        return NotificationResponse.model_validate(notification)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.post("/{notification_id}/read", response_model=SuccessResponse)
async def mark_as_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark a notification as read.
    """
    notification_service = NotificationService(db)

    try:
        await notification_service.mark_as_read(
            notification_id=notification_id,
            user_id=current_user.id,
        )
        return SuccessResponse(message="Notification marked as read")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.post("/read-all", response_model=SuccessResponse)
async def mark_all_as_read(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark all notifications as read.
    """
    notification_service = NotificationService(db)
    await notification_service.mark_all_as_read(current_user.id)
    return SuccessResponse(message="All notifications marked as read")


@router.delete("/{notification_id}", response_model=SuccessResponse)
async def delete_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a notification.
    """
    notification_service = NotificationService(db)

    try:
        await notification_service.delete_notification(
            notification_id=notification_id,
            user_id=current_user.id,
        )
        return SuccessResponse(message="Notification deleted")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


# Admin notification endpoints
@router.post("/send", response_model=SuccessResponse)
@require_permissions(Permission.SEND_NOTIFICATION)
async def send_notification(
    notification_data: NotificationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Send a notification to a user.

    Requires: SEND_NOTIFICATION permission
    """
    notification_service = NotificationService(db)

    try:
        await notification_service.send_notification(
            created_by=current_user.id,
            **notification_data.model_dump(),
        )
        return SuccessResponse(message="Notification sent successfully")
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


@router.post("/send-bulk", response_model=SuccessResponse)
@require_permissions(Permission.SEND_NOTIFICATION)
async def send_bulk_notification(
    bulk_data: BulkNotificationRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Send a notification to multiple users.

    Requires: SEND_NOTIFICATION permission
    """
    notification_service = NotificationService(db)

    try:
        count = await notification_service.send_bulk_notification(
            user_ids=bulk_data.user_ids,
            notification_type=bulk_data.notification_type,
            title=bulk_data.title,
            message=bulk_data.message,
            data=bulk_data.data,
            created_by=current_user.id,
        )
        return SuccessResponse(message=f"Notification sent to {count} users")
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Template endpoints
@router.get("/templates", response_model=list[NotificationTemplateResponse])
@require_permissions(Permission.MANAGE_NOTIFICATION_TEMPLATES)
async def list_templates(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    notification_type: Optional[NotificationType] = None,
    is_active: bool = True,
):
    """
    List notification templates.

    Requires: MANAGE_NOTIFICATION_TEMPLATES permission
    """
    notification_service = NotificationService(db)

    templates = await notification_service.get_templates(
        notification_type=notification_type,
        is_active=is_active,
    )

    return [NotificationTemplateResponse.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=NotificationTemplateResponse)
@require_permissions(Permission.MANAGE_NOTIFICATION_TEMPLATES)
async def get_template(
    template_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific notification template.

    Requires: MANAGE_NOTIFICATION_TEMPLATES permission
    """
    notification_service = NotificationService(db)

    try:
        template = await notification_service.get_template(template_id)
        return NotificationTemplateResponse.model_validate(template)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )


@router.post("/templates", response_model=NotificationTemplateResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.MANAGE_NOTIFICATION_TEMPLATES)
async def create_template(
    template_data: NotificationTemplateCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a notification template.

    Requires: MANAGE_NOTIFICATION_TEMPLATES permission
    """
    notification_service = NotificationService(db)

    try:
        template = await notification_service.create_template(
            created_by=current_user.id,
            **template_data.model_dump(),
        )
        return NotificationTemplateResponse.model_validate(template)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
@require_permissions(Permission.MANAGE_NOTIFICATION_TEMPLATES)
async def update_template(
    template_id: UUID,
    template_data: NotificationTemplateUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a notification template.

    Requires: MANAGE_NOTIFICATION_TEMPLATES permission
    """
    notification_service = NotificationService(db)

    try:
        template = await notification_service.update_template(
            template_id=template_id,
            **template_data.model_dump(exclude_unset=True),
        )
        return NotificationTemplateResponse.model_validate(template)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/templates/{template_id}", response_model=SuccessResponse)
@require_permissions(Permission.MANAGE_NOTIFICATION_TEMPLATES)
async def delete_template(
    template_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a notification template.

    Requires: MANAGE_NOTIFICATION_TEMPLATES permission
    """
    notification_service = NotificationService(db)

    try:
        await notification_service.delete_template(template_id)
        return SuccessResponse(message="Template deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
