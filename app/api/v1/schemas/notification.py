"""Notification schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import NotificationChannel, NotificationPriority, NotificationStatus
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# NOTIFICATION TEMPLATE
# ==========================================


class NotificationTemplateBase(BaseSchema):
    """Base notification template schema."""

    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    subject: Optional[str] = Field(None, max_length=255)
    body: str
    channel: NotificationChannel
    variables: Optional[list[str]] = None
    description: Optional[str] = None


class NotificationTemplateCreate(NotificationTemplateBase):
    """Create notification template schema."""

    pass


class NotificationTemplateUpdate(BaseSchema):
    """Update notification template schema."""

    name: Optional[str] = Field(None, max_length=100)
    subject: Optional[str] = Field(None, max_length=255)
    body: Optional[str] = None
    channel: Optional[NotificationChannel] = None
    variables: Optional[list[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(IDTimestampSchema, NotificationTemplateBase):
    """Notification template response schema."""

    is_active: bool


class NotificationTemplateListResponse(BaseSchema):
    """Notification template list item."""

    id: UUID
    name: str
    code: str
    channel: NotificationChannel
    is_active: bool


# ==========================================
# NOTIFICATION
# ==========================================


class NotificationBase(BaseSchema):
    """Base notification schema."""

    title: str = Field(..., max_length=255)
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    action_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = None


class NotificationCreate(NotificationBase):
    """Create notification schema."""

    user_id: UUID
    template_id: Optional[UUID] = None


class NotificationBulkCreate(BaseSchema):
    """Create bulk notifications schema."""

    user_ids: list[UUID] = Field(..., min_length=1)
    title: str = Field(..., max_length=255)
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    action_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = None


class NotificationResponse(IDTimestampSchema, NotificationBase):
    """Notification response schema."""

    user_id: UUID
    template_id: Optional[UUID] = None
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None


class NotificationListResponse(BaseSchema):
    """Notification list item."""

    id: UUID
    user_id: UUID
    title: str
    message: str
    priority: NotificationPriority
    channel: NotificationChannel
    status: NotificationStatus
    is_read: bool
    created_at: datetime


class NotificationDetailResponse(NotificationResponse):
    """Detailed notification response."""

    template_name: Optional[str] = None


# ==========================================
# NOTIFICATION ACTIONS
# ==========================================


class MarkReadRequest(BaseSchema):
    """Mark notification as read request."""

    notification_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class MarkAllReadResponse(BaseSchema):
    """Mark all as read response."""

    marked_count: int
    message: str = "Notifications marked as read"


# ==========================================
# NOTIFICATION FILTERS
# ==========================================


class NotificationFilterParams(BaseSchema):
    """Notification filter parameters."""

    user_id: Optional[UUID] = None
    channel: Optional[NotificationChannel] = None
    priority: Optional[NotificationPriority] = None
    status: Optional[NotificationStatus] = None
    is_read: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ==========================================
# NOTIFICATION PREFERENCES
# ==========================================


class NotificationPreferences(BaseSchema):
    """User notification preferences."""

    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    appointment_reminders: bool = True
    lab_results: bool = True
    billing_alerts: bool = True
    promotional: bool = False


class NotificationPreferencesUpdate(BaseSchema):
    """Update notification preferences."""

    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    appointment_reminders: Optional[bool] = None
    lab_results: Optional[bool] = None
    billing_alerts: Optional[bool] = None
    promotional: Optional[bool] = None


# ==========================================
# NOTIFICATION STATISTICS
# ==========================================


class NotificationStatsResponse(BaseSchema):
    """Notification statistics response."""

    total_notifications: int
    sent: int
    delivered: int
    failed: int
    read: int
    unread: int
    by_channel: dict[str, int]
    by_priority: dict[str, int]
    delivery_rate: float = 0.0
    read_rate: float = 0.0


class UserNotificationSummary(BaseSchema):
    """User notification summary."""

    user_id: UUID
    total: int
    unread: int
    high_priority_unread: int
