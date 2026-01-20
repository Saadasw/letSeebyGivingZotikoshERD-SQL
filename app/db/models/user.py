"""User related models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import UserRole

if TYPE_CHECKING:
    from app.db.models.doctor import DoctorProfile
    from app.db.models.staff import StaffProfile
    from app.db.models.patient import PatientProfile


class User(Base, UUIDMixin, TimestampMixin):
    """User model - core authentication entity."""

    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.PATIENT,
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    doctor_profile: Mapped[Optional["DoctorProfile"]] = relationship(
        "DoctorProfile", back_populates="user", uselist=False, lazy="joined"
    )
    staff_profile: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="user", uselist=False, lazy="joined"
    )
    patient_profile: Mapped[Optional["PatientProfile"]] = relationship(
        "PatientProfile", back_populates="user", uselist=False, lazy="joined"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    profile_images: Mapped[list["ProfileImage"]] = relationship(
        "ProfileImage", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    @property
    def is_doctor(self) -> bool:
        """Check if user is doctor."""
        return self.role == UserRole.DOCTOR

    @property
    def is_staff(self) -> bool:
        """Check if user is staff."""
        return self.role == UserRole.STAFF

    @property
    def is_patient(self) -> bool:
        """Check if user is patient."""
        return self.role == UserRole.PATIENT

    @property
    def is_email_verified(self) -> bool:
        """Check if email is verified."""
        return self.email_verified_at is not None

    @property
    def needs_profile_setup(self) -> bool:
        """Check if user needs to complete profile setup (set password)."""
        return not self.profile_completed or self.password is None

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"


class UserSession(Base, UUIDMixin):
    """User session for refresh token management."""

    __tablename__ = "user_session"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession {self.id} (user={self.user_id})>"


class ProfileImage(Base, UUIDMixin):
    """Profile image storage."""

    __tablename__ = "profile_image"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile_images")

    def __repr__(self) -> str:
        return f"<ProfileImage {self.id} (user={self.user_id})>"
