"""Notification repository."""

from datetime import datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import NotificationChannel, NotificationPriority, NotificationStatus
from app.db.models.notification import Notification, NotificationTemplate
from .base import BaseRepository


class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    """Repository for NotificationTemplate model."""

    def __init__(self, db: AsyncSession):
        super().__init__(NotificationTemplate, db)

    async def get_by_code(self, code: str) -> Optional[NotificationTemplate]:
        """Get template by code."""
        query = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.code == code,
                NotificationTemplate.is_active == True,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_templates_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Sequence[NotificationTemplate]:
        """Get list of templates with filters."""
        query = select(NotificationTemplate)

        conditions = []

        if channel:
            conditions.append(NotificationTemplate.channel == channel)
        if is_active is not None:
            conditions.append(NotificationTemplate.is_active == is_active)
        if search:
            conditions.append(
                or_(
                    NotificationTemplate.name.ilike(f"%{search}%"),
                    NotificationTemplate.code.ilike(f"%{search}%"),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(NotificationTemplate.name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_notifications_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[UUID] = None,
        channel: Optional[NotificationChannel] = None,
        priority: Optional[NotificationPriority] = None,
        status: Optional[NotificationStatus] = None,
        is_read: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Sequence[Notification]:
        """Get list of notifications with filters."""
        query = select(Notification)

        conditions = []

        if user_id:
            conditions.append(Notification.user_id == user_id)
        if channel:
            conditions.append(Notification.channel == channel)
        if priority:
            conditions.append(Notification.priority == priority)
        if status:
            conditions.append(Notification.status == status)
        if is_read is not None:
            if is_read:
                conditions.append(Notification.read_at.isnot(None))
            else:
                conditions.append(Notification.read_at.is_(None))
        if date_from:
            conditions.append(Notification.created_at >= date_from)
        if date_to:
            conditions.append(Notification.created_at <= date_to)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Notification.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_notifications(
        self,
        user_id: UUID,
        *,
        is_read: Optional[bool] = None,
    ) -> int:
        """Count notifications for a user."""
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id
        )

        if is_read is not None:
            if is_read:
                query = query.where(Notification.read_at.isnot(None))
            else:
                query = query.where(Notification.read_at.is_(None))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.read_at.is_(None))

        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def mark_as_read(
        self,
        notification_id: UUID,
    ) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=datetime.utcnow())
        )
        await self.db.flush()
        return result.rowcount > 0

    async def mark_many_as_read(
        self,
        notification_ids: list[UUID],
    ) -> int:
        """Mark multiple notifications as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id.in_(notification_ids),
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=datetime.utcnow())
        )
        await self.db.flush()
        return result.rowcount

    async def mark_all_as_read(
        self,
        user_id: UUID,
    ) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=datetime.utcnow())
        )
        await self.db.flush()
        return result.rowcount

    async def update_status(
        self,
        notification_id: UUID,
        status: NotificationStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update notification status."""
        update_data = {"status": status}

        if status == NotificationStatus.SENT:
            update_data["sent_at"] = datetime.utcnow()
        if error_message:
            update_data["error_message"] = error_message

        result = await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(**update_data)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def create_bulk(
        self,
        notifications_data: list[dict],
    ) -> list[Notification]:
        """Create multiple notifications."""
        notifications = [Notification(**data) for data in notifications_data]
        self.db.add_all(notifications)
        await self.db.flush()
        for n in notifications:
            await self.db.refresh(n)
        return notifications

    async def get_notification_stats(
        self,
        user_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get notification statistics."""
        conditions = []
        if user_id:
            conditions.append(Notification.user_id == user_id)

        # Total
        total_query = select(func.count(Notification.id))
        if conditions:
            total_query = total_query.where(and_(*conditions))
        total = await self.db.execute(total_query)

        # By status
        status_query = (
            select(Notification.status, func.count(Notification.id))
            .group_by(Notification.status)
        )
        if conditions:
            status_query = status_query.where(and_(*conditions))
        status_result = await self.db.execute(status_query)
        by_status = {str(s.value): c for s, c in status_result.all()}

        # By channel
        channel_query = (
            select(Notification.channel, func.count(Notification.id))
            .group_by(Notification.channel)
        )
        if conditions:
            channel_query = channel_query.where(and_(*conditions))
        channel_result = await self.db.execute(channel_query)
        by_channel = {str(c.value): cnt for c, cnt in channel_result.all()}

        # Unread count
        unread_query = select(func.count(Notification.id)).where(
            Notification.read_at.is_(None)
        )
        if conditions:
            unread_query = unread_query.where(and_(*conditions))
        unread = await self.db.execute(unread_query)

        total_count = total.scalar() or 0
        sent = by_status.get("sent", 0) + by_status.get("delivered", 0)
        delivery_rate = (sent / total_count * 100) if total_count > 0 else 0

        read_count = total_count - (unread.scalar() or 0)
        read_rate = (read_count / total_count * 100) if total_count > 0 else 0

        return {
            "total_notifications": total_count,
            "sent": by_status.get("sent", 0),
            "delivered": by_status.get("delivered", 0),
            "failed": by_status.get("failed", 0),
            "read": read_count,
            "unread": unread.scalar() or 0,
            "by_channel": by_channel,
            "by_status": by_status,
            "delivery_rate": round(delivery_rate, 2),
            "read_rate": round(read_rate, 2),
        }
