"""
OTP (One-Time Password) service for email verification.
"""
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.email import email_service

logger = logging.getLogger(__name__)

# OTP configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60


class OTPService:
    """Service for OTP generation and verification."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_otp(self) -> str:
        """Generate a random 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=OTP_LENGTH))

    async def _get_otp_model(self):
        """Dynamically import OTP model to avoid circular imports."""
        from app.db.models.otp import OTP, OTPPurpose
        return OTP, OTPPurpose

    async def send_otp(
        self,
        email: str,
        purpose: str = "email_verification"
    ) -> Tuple[bool, str]:
        """
        Generate and send OTP to email.

        Args:
            email: Email address to send OTP to
            purpose: Purpose of OTP (email_verification, password_reset)

        Returns:
            Tuple of (success, message)
        """
        OTP, OTPPurpose = await self._get_otp_model()

        # Check for recent OTP (cooldown)
        cooldown_time = datetime.utcnow() - timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
        recent_otp_query = select(OTP).where(
            and_(
                OTP.email == email.lower(),
                OTP.purpose == OTPPurpose(purpose),
                OTP.created_at > cooldown_time,
                OTP.is_verified == False
            )
        )
        result = await self.db.execute(recent_otp_query)
        recent_otp = result.scalar_one_or_none()

        if recent_otp:
            wait_seconds = OTP_RESEND_COOLDOWN_SECONDS - (datetime.utcnow() - recent_otp.created_at).seconds
            return False, f"Please wait {wait_seconds} seconds before requesting a new OTP"

        # Invalidate any existing OTPs for this email and purpose
        await self.db.execute(
            delete(OTP).where(
                and_(
                    OTP.email == email.lower(),
                    OTP.purpose == OTPPurpose(purpose),
                    OTP.is_verified == False
                )
            )
        )

        # Generate new OTP
        otp_code = self._generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        # Create OTP record
        otp_record = OTP(
            email=email.lower(),
            otp_code=otp_code,
            purpose=OTPPurpose(purpose),
            expires_at=expires_at,
            max_attempts=MAX_OTP_ATTEMPTS,
        )
        self.db.add(otp_record)
        await self.db.commit()

        # Send OTP email
        email_sent = await email_service.send_otp(email, otp_code)

        if email_sent:
            logger.info(f"OTP sent successfully to {email}")
            return True, "OTP sent successfully. Please check your email."
        else:
            logger.error(f"Failed to send OTP to {email}")
            return False, "Failed to send OTP. Please try again."

    async def verify_otp(
        self,
        email: str,
        otp_code: str,
        purpose: str = "email_verification"
    ) -> Tuple[bool, str]:
        """
        Verify OTP code.

        Args:
            email: Email address
            otp_code: OTP code to verify
            purpose: Purpose of OTP

        Returns:
            Tuple of (success, message)
        """
        OTP, OTPPurpose = await self._get_otp_model()

        # Find the OTP record
        otp_query = select(OTP).where(
            and_(
                OTP.email == email.lower(),
                OTP.purpose == OTPPurpose(purpose),
                OTP.is_verified == False
            )
        ).order_by(OTP.created_at.desc())

        result = await self.db.execute(otp_query)
        otp_record = result.scalar_one_or_none()

        if not otp_record:
            return False, "No OTP found. Please request a new one."

        # Check if expired
        if otp_record.is_expired():
            return False, "OTP has expired. Please request a new one."

        # Check max attempts
        if otp_record.is_max_attempts_reached():
            return False, "Maximum attempts reached. Please request a new OTP."

        # Verify OTP
        if otp_record.otp_code != otp_code:
            otp_record.attempts += 1
            await self.db.commit()
            remaining = otp_record.max_attempts - otp_record.attempts
            return False, f"Invalid OTP. {remaining} attempts remaining."

        # Mark as verified
        otp_record.is_verified = True
        otp_record.verified_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"OTP verified successfully for {email}")
        return True, "OTP verified successfully."

    async def is_email_verified(
        self,
        email: str,
        purpose: str = "email_verification"
    ) -> bool:
        """
        Check if email has been verified via OTP.

        Args:
            email: Email address
            purpose: Purpose of OTP

        Returns:
            True if email was verified
        """
        OTP, OTPPurpose = await self._get_otp_model()

        # Find verified OTP within reasonable time (e.g., last 30 minutes)
        recent_time = datetime.utcnow() - timedelta(minutes=30)

        otp_query = select(OTP).where(
            and_(
                OTP.email == email.lower(),
                OTP.purpose == OTPPurpose(purpose),
                OTP.is_verified == True,
                OTP.verified_at > recent_time
            )
        )

        result = await self.db.execute(otp_query)
        return result.scalar_one_or_none() is not None

    async def cleanup_expired_otps(self) -> int:
        """
        Clean up expired OTP records.

        Returns:
            Number of records deleted
        """
        OTP, _ = await self._get_otp_model()

        result = await self.db.execute(
            delete(OTP).where(OTP.expires_at < datetime.utcnow())
        )
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired OTP records")
        return count
