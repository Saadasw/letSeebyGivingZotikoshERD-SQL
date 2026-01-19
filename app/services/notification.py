"""Notification service."""

from datetime import datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)
from app.db.models.notification import Notification, NotificationTemplate
from app.repositories.notification import (
    NotificationRepository,
    NotificationTemplateRepository,
)


class NotificationService:
    """Notification management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.template_repo = NotificationTemplateRepository(db)

    # Templates
    async def get_template(self, template_id: UUID) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        return await self.template_repo.get(template_id)

    async def get_template_by_code(self, code: str) -> Optional[NotificationTemplate]:
        """Get template by code."""
        return await self.template_repo.get_by_code(code)

    async def get_templates(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Sequence[NotificationTemplate]:
        """Get list of templates."""
        return await self.template_repo.get_templates_list(
            skip=skip,
            limit=limit,
            channel=channel,
            is_active=is_active,
            search=search,
        )

    async def create_template(self, **template_data) -> NotificationTemplate:
        """Create a new template."""
        template = await self.template_repo.create(template_data)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(
        self,
        template_id: UUID,
        **update_data,
    ) -> Optional[NotificationTemplate]:
        """Update template."""
        updated = await self.template_repo.update(template_id, update_data)
        await self.db.commit()
        return updated

    # Notifications
    async def get_notification(self, notification_id: UUID) -> Optional[Notification]:
        """Get notification by ID."""
        return await self.notification_repo.get(notification_id)

    async def get_notifications(
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
        """Get list of notifications."""
        return await self.notification_repo.get_notifications_list(
            skip=skip,
            limit=limit,
            user_id=user_id,
            channel=channel,
            priority=priority,
            status=status,
            is_read=is_read,
            date_from=date_from,
            date_to=date_to,
        )

    async def count_notifications(
        self,
        user_id: UUID,
        *,
        is_read: Optional[bool] = None,
    ) -> int:
        """Count notifications for a user."""
        return await self.notification_repo.count_notifications(
            user_id, is_read=is_read
        )

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Notification]:
        """Get notifications for a user."""
        return await self.notification_repo.get_user_notifications(
            user_id,
            unread_only=unread_only,
            limit=limit,
        )

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications."""
        return await self.notification_repo.get_unread_count(user_id)

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        template_id: Optional[UUID] = None,
    ) -> Notification:
        """Send a notification to a user."""
        notification = await self.notification_repo.create({
            "user_id": user_id,
            "title": title,
            "message": message,
            "channel": channel,
            "priority": priority,
            "action_url": action_url,
            "metadata": metadata,
            "template_id": template_id,
            "status": NotificationStatus.PENDING,
        })

        # For in-app notifications, mark as sent immediately
        if channel == NotificationChannel.IN_APP:
            await self.notification_repo.update_status(
                notification.id,
                NotificationStatus.SENT,
            )

        await self.db.commit()
        await self.db.refresh(notification)

        return notification

    async def send_notification_from_template(
        self,
        user_id: UUID,
        template_code: str,
        variables: Optional[dict] = None,
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Notification:
        """Send notification using a template."""
        template = await self.template_repo.get_by_code(template_code)
        if not template:
            raise NotFoundError(f"Template '{template_code}' not found")

        # Replace variables in template
        title = template.subject or template.name
        message = template.body

        if variables:
            for key, value in variables.items():
                title = title.replace(f"{{{key}}}", str(value))
                message = message.replace(f"{{{key}}}", str(value))

        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            channel=template.channel,
            action_url=action_url,
            metadata=metadata,
            template_id=template.id,
        )

    async def send_bulk_notification(
        self,
        user_ids: list[UUID],
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> list[Notification]:
        """Send notification to multiple users."""
        notifications_data = [
            {
                "user_id": user_id,
                "title": title,
                "message": message,
                "channel": channel,
                "priority": priority,
                "action_url": action_url,
                "metadata": metadata,
                "status": NotificationStatus.PENDING
                if channel != NotificationChannel.IN_APP
                else NotificationStatus.SENT,
            }
            for user_id in user_ids
        ]

        notifications = await self.notification_repo.create_bulk(notifications_data)
        await self.db.commit()

        return notifications

    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Mark a notification as read."""
        notification = await self.notification_repo.get(notification_id)
        if not notification:
            raise NotFoundError("Notification not found")

        if notification.user_id != user_id:
            raise NotFoundError("Notification not found")

        result = await self.notification_repo.mark_as_read(notification_id)
        await self.db.commit()

        return result

    async def mark_many_as_read(
        self,
        notification_ids: list[UUID],
        user_id: UUID,
    ) -> int:
        """Mark multiple notifications as read."""
        # Verify ownership
        for nid in notification_ids:
            notification = await self.notification_repo.get(nid)
            if not notification or notification.user_id != user_id:
                notification_ids.remove(nid)

        count = await self.notification_repo.mark_many_as_read(notification_ids)
        await self.db.commit()

        return count

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        count = await self.notification_repo.mark_all_as_read(user_id)
        await self.db.commit()
        return count

    async def get_notification_stats(
        self,
        user_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get notification statistics."""
        return await self.notification_repo.get_notification_stats(user_id)

    async def get_user_notification_summary(
        self,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Get notification summary for a user."""
        total = await self.notification_repo.count_notifications(user_id)
        unread = await self.notification_repo.get_unread_count(user_id)

        # High priority unread
        high_priority = await self.notification_repo.count_notifications(
            user_id, is_read=False
        )

        return {
            "user_id": user_id,
            "total": total,
            "unread": unread,
            "high_priority_unread": high_priority,
        }
