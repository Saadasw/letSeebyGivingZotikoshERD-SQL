"""Audit and settings schemas."""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, IDTimestampSchema


# ==========================================
# AUDIT LOG
# ==========================================


class AuditLogResponse(IDTimestampSchema):
    """Audit log response schema."""

    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    old_values: Optional[dict[str, Any]] = None
    new_values: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    # Joined fields
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class AuditLogListResponse(BaseSchema):
    """Audit log list item."""

    id: UUID
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


class AuditLogDetailResponse(AuditLogResponse):
    """Detailed audit log response."""

    changes_summary: Optional[list[str]] = None


# ==========================================
# AUDIT LOG FILTERS
# ==========================================


class AuditLogFilterParams(BaseSchema):
    """Audit log filter parameters."""

    user_id: Optional[UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    ip_address: Optional[str] = None
    search: Optional[str] = Field(None, description="Search in action or resource")


# ==========================================
# AUDIT STATISTICS
# ==========================================


class AuditStatsResponse(BaseSchema):
    """Audit statistics response."""

    total_logs: int
    by_action: dict[str, int]
    by_resource_type: dict[str, int]
    by_user: dict[str, int]
    recent_activity: list[AuditLogListResponse]


class UserActivityReport(BaseSchema):
    """User activity report."""

    user_id: UUID
    user_name: str
    total_actions: int
    by_action: dict[str, int]
    last_activity: Optional[datetime] = None


# ==========================================
# SYSTEM SETTINGS
# ==========================================


class SystemSettingBase(BaseSchema):
    """Base system setting schema."""

    key: str = Field(..., max_length=100)
    value: str
    category: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_public: bool = False


class SystemSettingCreate(SystemSettingBase):
    """Create system setting schema."""

    pass


class SystemSettingUpdate(BaseSchema):
    """Update system setting schema."""

    value: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class SystemSettingResponse(IDTimestampSchema, SystemSettingBase):
    """System setting response schema."""

    is_active: bool
    updated_by: Optional[UUID] = None
    # Joined fields
    updated_by_name: Optional[str] = None


class SystemSettingListResponse(BaseSchema):
    """System setting list item."""

    id: UUID
    key: str
    value: str
    category: str
    is_public: bool
    is_active: bool


# ==========================================
# SETTINGS FILTERS
# ==========================================


class SystemSettingFilterParams(BaseSchema):
    """System setting filter parameters."""

    category: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="Search in key or description")


# ==========================================
# BULK SETTINGS
# ==========================================


class BulkSettingUpdate(BaseSchema):
    """Bulk setting update item."""

    key: str
    value: str


class BulkSettingsUpdateRequest(BaseSchema):
    """Bulk settings update request."""

    settings: list[BulkSettingUpdate] = Field(..., min_length=1)


class BulkSettingsUpdateResponse(BaseSchema):
    """Bulk settings update response."""

    updated_count: int
    failed_keys: list[str] = []
    message: str


# ==========================================
# APP CONFIGURATION
# ==========================================


class AppConfigResponse(BaseSchema):
    """Public application configuration."""

    app_name: str
    app_version: str
    maintenance_mode: bool = False
    features: dict[str, bool] = {}
    settings: dict[str, Any] = {}
