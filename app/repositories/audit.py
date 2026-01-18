"""Audit and settings repository."""

from datetime import datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.audit import AuditLog
from app.db.models.settings import SystemSetting
from app.db.models.user import User
from .base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model."""

    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def get_with_user(self, id: UUID) -> Optional[AuditLog]:
        """Get audit log with user details."""
        query = (
            select(AuditLog)
            .where(AuditLog.id == id)
            .options(joinedload(AuditLog.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_logs_list(
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
        """Get list of audit logs with filters."""
        query = select(AuditLog).options(joinedload(AuditLog.user))

        conditions = []

        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
        if date_from:
            conditions.append(AuditLog.created_at >= date_from)
        if date_to:
            conditions.append(AuditLog.created_at <= date_to)
        if ip_address:
            conditions.append(AuditLog.ip_address == ip_address)

        if search:
            conditions.append(
                or_(
                    AuditLog.action.ilike(f"%{search}%"),
                    AuditLog.resource_type.ilike(f"%{search}%"),
                    AuditLog.resource_id.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def count_logs(
        self,
        *,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        """Count audit logs matching filters."""
        query = select(func.count(AuditLog.id))

        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if date_from:
            conditions.append(AuditLog.created_at >= date_from)
        if date_to:
            conditions.append(AuditLog.created_at <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_user_activity(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> Sequence[AuditLog]:
        """Get recent activity for a user."""
        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> Sequence[AuditLog]:
        """Get audit history for a specific resource."""
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
            )
            .options(joinedload(AuditLog.user))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

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
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_audit_stats(self) -> dict[str, Any]:
        """Get audit log statistics."""
        # Total logs
        total_query = select(func.count(AuditLog.id))
        total = await self.db.execute(total_query)

        # By action
        action_query = (
            select(AuditLog.action, func.count(AuditLog.id))
            .group_by(AuditLog.action)
        )
        action_result = await self.db.execute(action_query)
        by_action = {a: c for a, c in action_result.all()}

        # By resource type
        resource_query = (
            select(AuditLog.resource_type, func.count(AuditLog.id))
            .group_by(AuditLog.resource_type)
        )
        resource_result = await self.db.execute(resource_query)
        by_resource = {r: c for r, c in resource_result.all()}

        # By user (top 10)
        user_query = (
            select(AuditLog.user_id, func.count(AuditLog.id))
            .where(AuditLog.user_id.isnot(None))
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        user_result = await self.db.execute(user_query)
        by_user = {str(u): c for u, c in user_result.all()}

        return {
            "total_logs": total.scalar() or 0,
            "by_action": by_action,
            "by_resource_type": by_resource,
            "by_user": by_user,
        }


class SystemSettingRepository(BaseRepository[SystemSetting]):
    """Repository for SystemSetting model."""

    def __init__(self, db: AsyncSession):
        super().__init__(SystemSetting, db)

    async def get_by_key(self, key: str) -> Optional[SystemSetting]:
        """Get setting by key."""
        query = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_value(
        self,
        key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Get setting value by key."""
        setting = await self.get_by_key(key)
        return setting.value if setting and setting.is_active else default

    async def get_settings_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Sequence[SystemSetting]:
        """Get list of settings with filters."""
        query = select(SystemSetting)

        conditions = []

        if category:
            conditions.append(SystemSetting.category == category)
        if is_public is not None:
            conditions.append(SystemSetting.is_public == is_public)
        if is_active is not None:
            conditions.append(SystemSetting.is_active == is_active)
        if search:
            conditions.append(
                or_(
                    SystemSetting.key.ilike(f"%{search}%"),
                    SystemSetting.description.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(SystemSetting.category, SystemSetting.key)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_category(
        self,
        category: str,
        *,
        active_only: bool = True,
    ) -> Sequence[SystemSetting]:
        """Get settings by category."""
        query = select(SystemSetting).where(SystemSetting.category == category)

        if active_only:
            query = query.where(SystemSetting.is_active == True)

        query = query.order_by(SystemSetting.key)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_public_settings(self) -> Sequence[SystemSetting]:
        """Get all public settings."""
        query = (
            select(SystemSetting)
            .where(
                and_(
                    SystemSetting.is_public == True,
                    SystemSetting.is_active == True,
                )
            )
            .order_by(SystemSetting.category, SystemSetting.key)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_categories(self) -> Sequence[str]:
        """Get all unique categories."""
        query = select(SystemSetting.category).distinct()
        result = await self.db.execute(query)
        return [r[0] for r in result.all()]

    async def set_value(
        self,
        key: str,
        value: str,
        updated_by: Optional[UUID] = None,
    ) -> Optional[SystemSetting]:
        """Set a setting value."""
        setting = await self.get_by_key(key)
        if not setting:
            return None

        return await self.update(
            setting.id,
            {
                "value": value,
                "updated_by": updated_by,
            },
        )

    async def bulk_update(
        self,
        settings: list[dict[str, str]],
        updated_by: Optional[UUID] = None,
    ) -> tuple[int, list[str]]:
        """Bulk update settings. Returns (updated_count, failed_keys)."""
        updated = 0
        failed = []

        for item in settings:
            key = item.get("key")
            value = item.get("value")

            if not key or value is None:
                continue

            result = await self.set_value(key, value, updated_by)
            if result:
                updated += 1
            else:
                failed.append(key)

        return updated, failed

    async def create_or_update(
        self,
        key: str,
        value: str,
        category: str,
        description: Optional[str] = None,
        is_public: bool = False,
        updated_by: Optional[UUID] = None,
    ) -> SystemSetting:
        """Create or update a setting."""
        existing = await self.get_by_key(key)

        if existing:
            return await self.update(
                existing.id,
                {
                    "value": value,
                    "description": description,
                    "is_public": is_public,
                    "updated_by": updated_by,
                },
            )

        return await self.create({
            "key": key,
            "value": value,
            "category": category,
            "description": description,
            "is_public": is_public,
            "updated_by": updated_by,
        })
