"""Authentication service."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.repositories.user import UserRepository
from app.repositories.patient import PatientRepository


class AuthService:
    """Authentication service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.patient_repo = PatientRepository(db)

    async def authenticate(
        self,
        email: str,
        password: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and return tokens.

        Returns:
            Tuple of (user, access_token, refresh_token)
        """
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # Update last login
        await self.user_repo.update_last_login(user.id)

        # Create tokens
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            department=user.department.value if user.department else None,
        )

        refresh_token = create_refresh_token(subject=str(user.id))

        # Create session
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.user_repo.create_session(
            user_id=user.id,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
        )

        await self.db.commit()

        return user, access_token, refresh_token

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> Tuple[str, str]:
        """
        Refresh access and refresh tokens.

        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        # Get session
        session = await self.user_repo.get_session_by_token(refresh_token)
        if not session:
            raise AuthenticationError("Session not found or expired")

        if session.expires_at and session.expires_at < datetime.utcnow():
            await self.user_repo.revoke_session(session.id)
            await self.db.commit()
            raise AuthenticationError("Session expired")

        # Get user
        user = await self.user_repo.get(session.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Revoke old session
        await self.user_repo.revoke_session(session.id)

        # Create new tokens
        new_access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            department=user.department.value if user.department else None,
        )

        new_refresh_token = create_refresh_token(subject=str(user.id))

        # Create new session
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.user_repo.create_session(
            user_id=user.id,
            refresh_token=new_refresh_token,
            device_info=session.device_info,
            ip_address=session.ip_address,
            expires_at=expires_at,
        )

        await self.db.commit()

        return new_access_token, new_refresh_token

    async def logout(
        self,
        refresh_token: str,
    ) -> bool:
        """Logout user by revoking session."""
        session = await self.user_repo.get_session_by_token(refresh_token)
        if session:
            await self.user_repo.revoke_session(session.id)
            await self.db.commit()
            return True
        return False

    async def logout_all(
        self,
        user_id: UUID,
        except_current: Optional[str] = None,
    ) -> int:
        """Logout user from all sessions."""
        except_session_id = None

        if except_current:
            session = await self.user_repo.get_session_by_token(except_current)
            if session:
                except_session_id = session.id

        count = await self.user_repo.revoke_all_sessions(
            user_id,
            except_session_id=except_session_id,
        )
        await self.db.commit()
        return count

    async def register_patient(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        **patient_data,
    ) -> User:
        """Register a new patient."""
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        # Create user
        user = await self.user_repo.create({
            "email": email,
            "hashed_password": get_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "role": UserRole.PATIENT,
            "is_active": True,
            "is_verified": False,
        })

        # Create patient profile
        await self.patient_repo.create({
            "user_id": user.id,
            **patient_data,
        })

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(current_password, user.hashed_password):
            raise ValidationError("Current password is incorrect")

        hashed = get_password_hash(new_password)
        result = await self.user_repo.update_password(user_id, hashed)

        if result:
            # Revoke all sessions except current
            await self.user_repo.revoke_all_sessions(user_id)
            await self.db.commit()

        return result

    async def verify_email(
        self,
        token: str,
    ) -> bool:
        """Verify user email with token."""
        payload = decode_token(token)
        if not payload or payload.get("type") != "email_verification":
            raise ValidationError("Invalid verification token")

        user_id = UUID(payload.get("sub"))
        result = await self.user_repo.verify_email(user_id)

        if result:
            await self.db.commit()

        return result

    async def get_active_sessions(
        self,
        user_id: UUID,
        current_token: Optional[str] = None,
    ) -> list:
        """Get active sessions for a user."""
        sessions = await self.user_repo.get_user_sessions(user_id, active_only=True)

        current_session_id = None
        if current_token:
            current = await self.user_repo.get_session_by_token(current_token)
            if current:
                current_session_id = current.id

        result = []
        for session in sessions:
            result.append({
                "session_id": session.id,
                "device_info": session.device_info,
                "ip_address": session.ip_address,
                "last_activity": session.last_activity,
                "created_at": session.created_at,
                "is_current": session.id == current_session_id,
            })

        return result

    async def revoke_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> bool:
        """Revoke a specific session."""
        # Verify session belongs to user
        sessions = await self.user_repo.get_user_sessions(user_id, active_only=True)
        session_ids = [s.id for s in sessions]

        if session_id not in session_ids:
            raise NotFoundError("Session not found")

        result = await self.user_repo.revoke_session(session_id)
        if result:
            await self.db.commit()

        return result
