"""Audit service."""

from datetime import datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.audit import AuditLog
from app.db.models.settings import SystemSetting
from app.repositories.audit import AuditLogRepository, SystemSettingRepository


class AuditService:
    """Audit and settings management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_repo = AuditLogRepository(db)
        self.setting_repo = SystemSettingRepository(db)

    # Audit Logs
    async def get_audit_log(self, log_id: UUID) -> Optional[AuditLog]:
        """Get audit log by ID."""
        return await self.audit_repo.get_with_user(log_id)

    async def get_audit_logs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Sequence[AuditLog]:
        """Get list of audit logs."""
        return await self.audit_repo.get_logs_list(
            skip=skip,
            limit=limit,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            date_from=date_from,
            date_to=date_to,
            ip_address=ip_address,
            search=search,
        )

    async def count_audit_logs(
        self,
        *,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        """Count audit logs."""
        return await self.audit_repo.count_logs(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            date_from=date_from,
            date_to=date_to,
        )

    async def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        log = await self.audit_repo.log_action(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        await self.db.commit()
        return log

    async def get_user_activity(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> Sequence[AuditLog]:
        """Get recent activity for a user."""
        return await self.audit_repo.get_user_activity(user_id, limit=limit)

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> Sequence[AuditLog]:
        """Get audit history for a specific resource."""
        return await self.audit_repo.get_resource_history(
            resource_type, resource_id, limit=limit
        )

    async def get_audit_stats(self) -> dict[str, Any]:
        """Get audit log statistics."""
        return await self.audit_repo.get_audit_stats()

    # System Settings
    async def get_setting(self, setting_id: UUID) -> Optional[SystemSetting]:
        """Get setting by ID."""
        return await self.setting_repo.get(setting_id)

    async def get_setting_by_key(self, key: str) -> Optional[SystemSetting]:
        """Get setting by key."""
        return await self.setting_repo.get_by_key(key)

    async def get_setting_value(
        self,
        key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Get setting value by key."""
        return await self.setting_repo.get_value(key, default)

    async def get_settings(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Sequence[SystemSetting]:
        """Get list of settings."""
        return await self.setting_repo.get_settings_list(
            skip=skip,
            limit=limit,
            category=category,
            is_public=is_public,
            is_active=is_active,
            search=search,
        )

    async def get_settings_by_category(
        self,
        category: str,
        *,
        active_only: bool = True,
    ) -> Sequence[SystemSetting]:
        """Get settings by category."""
        return await self.setting_repo.get_by_category(
            category, active_only=active_only
        )

    async def get_public_settings(self) -> Sequence[SystemSetting]:
        """Get all public settings."""
        return await self.setting_repo.get_public_settings()

    async def get_setting_categories(self) -> Sequence[str]:
        """Get all setting categories."""
        return await self.setting_repo.get_categories()

    async def create_setting(
        self,
        key: str,
        value: str,
        category: str,
        description: Optional[str] = None,
        is_public: bool = False,
        updated_by: Optional[UUID] = None,
    ) -> SystemSetting:
        """Create a new setting."""
        # Check if key exists
        existing = await self.setting_repo.get_by_key(key)
        if existing:
            from app.core.exceptions import ConflictError
            raise ConflictError("Setting key already exists")

        setting = await self.setting_repo.create({
            "key": key,
            "value": value,
            "category": category,
            "description": description,
            "is_public": is_public,
            "updated_by": updated_by,
        })

        await self.db.commit()
        await self.db.refresh(setting)

        return setting

    async def update_setting(
        self,
        setting_id: UUID,
        updated_by: Optional[UUID] = None,
        **update_data,
    ) -> Optional[SystemSetting]:
        """Update a setting."""
        setting = await self.setting_repo.get(setting_id)
        if not setting:
            raise NotFoundError("Setting not found")

        update_data["updated_by"] = updated_by
        updated = await self.setting_repo.update(setting_id, update_data)

        await self.db.commit()
        return updated

    async def set_setting_value(
        self,
        key: str,
        value: str,
        updated_by: Optional[UUID] = None,
    ) -> Optional[SystemSetting]:
        """Set a setting value by key."""
        setting = await self.setting_repo.set_value(key, value, updated_by)
        if setting:
            await self.db.commit()
        return setting

    async def bulk_update_settings(
        self,
        settings: list[dict[str, str]],
        updated_by: Optional[UUID] = None,
    ) -> tuple[int, list[str]]:
        """Bulk update settings."""
        updated, failed = await self.setting_repo.bulk_update(settings, updated_by)
        await self.db.commit()
        return updated, failed

    async def get_app_config(self) -> dict[str, Any]:
        """Get public application configuration."""
        settings = await self.setting_repo.get_public_settings()

        config = {
            "app_name": "Hospital Management System",
            "app_version": "1.0.0",
            "maintenance_mode": False,
            "features": {},
            "settings": {},
        }

        for setting in settings:
            if setting.category == "feature":
                config["features"][setting.key] = setting.value.lower() == "true"
            elif setting.key == "maintenance_mode":
                config["maintenance_mode"] = setting.value.lower() == "true"
            else:
                config["settings"][setting.key] = setting.value

        return config
