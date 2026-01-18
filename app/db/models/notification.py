"""Notification models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import NotificationType, NotificationPriority, NotificationChannel

if TYPE_CHECKING:
    from app.db.models.user import User


class NotificationTemplate(Base, UUIDMixin, TimestampMixin):
    """Notification template for generating notifications."""

    __tablename__ = "notification_template"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        ENUM(NotificationType, name="notification_type", create_type=False),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        ENUM(NotificationChannel, name="notification_channel", create_type=False),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    sms_template: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="template"
    )

    def __repr__(self) -> str:
        return f"<NotificationTemplate {self.code}>"


class Notification(Base, UUIDMixin):
    """User notification."""

    __tablename__ = "notification"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("notification_template.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        ENUM(NotificationType, name="notification_type", create_type=False),
        nullable=False,
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        ENUM(NotificationPriority, name="notification_priority", create_type=False),
        nullable=False,
        default=NotificationPriority.NORMAL,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        ENUM(NotificationChannel, name="notification_channel", create_type=False),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    template: Mapped[Optional["NotificationTemplate"]] = relationship(
        "NotificationTemplate", back_populates="notifications"
    )

    @property
    def is_expired(self) -> bool:
        """Check if notification is expired."""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()

    def __repr__(self) -> str:
        return f"<Notification {self.title[:30]}>"
