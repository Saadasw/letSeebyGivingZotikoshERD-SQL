"""
OTP (One-Time Password) model for email verification.
"""
from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class OTPPurpose(str, enum.Enum):
    """OTP purpose types."""
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    PHONE_VERIFICATION = "phone_verification"


class OTP(Base, UUIDMixin):
    """OTP storage for verification."""

    __tablename__ = "otp"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    purpose: Mapped[OTPPurpose] = mapped_column(
        ENUM(OTPPurpose, name="otp_purpose", create_type=False),
        nullable=False,
        default=OTPPurpose.EMAIL_VERIFICATION
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def is_expired(self) -> bool:
        """Check if OTP has expired."""
        if self.expires_at.tzinfo:
            return datetime.utcnow() > self.expires_at.replace(tzinfo=None)
        return datetime.utcnow() > self.expires_at

    def is_max_attempts_reached(self) -> bool:
        """Check if max attempts reached."""
        return self.attempts >= self.max_attempts

    def __repr__(self) -> str:
        return f"<OTP {self.email} ({self.purpose.value})>"
