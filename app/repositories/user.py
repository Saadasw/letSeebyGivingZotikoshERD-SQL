"""User repository."""

from datetime import datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.enums import UserRole, StaffDepartment
from app.db.models.user import User, UserSession, ProfileImage
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_profile(self, user_id: UUID) -> Optional[User]:
        """Get user with related profile."""
        query = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.patient_profile),
                selectinload(User.doctor_profile),
                selectinload(User.staff_profile),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_role(
        self,
        role: UserRole,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> Sequence[User]:
        """Get users by role."""
        query = select(User).where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_department(
        self,
        department: StaffDepartment,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[User]:
        """Get users by department."""
        query = (
            select(User)
            .where(User.department == department)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_users(
        self,
        search_term: str,
        *,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        department: Optional[StaffDepartment] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[User]:
        """Search users by name or email."""
        query = select(User).where(
            or_(
                User.first_name.ilike(f"%{search_term}%"),
                User.last_name.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%"),
            )
        )

        if role:
            query = query.where(User.role == role)
        if department:
            query = query.where(User.department == department)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.utcnow())
        )
        await self.db.flush()

    async def update_password(
        self,
        user_id: UUID,
        hashed_password: str,
    ) -> bool:
        """Update user's password."""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def verify_email(self, user_id: UUID) -> bool:
        """Mark user's email as verified."""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_verified=True)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def get_user_stats(self) -> dict[str, Any]:
        """Get user statistics."""
        # Total users
        total_query = select(func.count(User.id))
        total = await self.db.execute(total_query)

        # Active users
        active_query = select(func.count(User.id)).where(User.is_active == True)
        active = await self.db.execute(active_query)

        # Verified users
        verified_query = select(func.count(User.id)).where(User.is_verified == True)
        verified = await self.db.execute(verified_query)

        # Users by role
        role_query = select(User.role, func.count(User.id)).group_by(User.role)
        role_result = await self.db.execute(role_query)
        by_role = {str(r.value): c for r, c in role_result.all()}

        # Users by department
        dept_query = (
            select(User.department, func.count(User.id))
            .where(User.department.isnot(None))
            .group_by(User.department)
        )
        dept_result = await self.db.execute(dept_query)
        by_department = {str(d.value): c for d, c in dept_result.all() if d}

        return {
            "total_users": total.scalar() or 0,
            "active_users": active.scalar() or 0,
            "inactive_users": (total.scalar() or 0) - (active.scalar() or 0),
            "verified_users": verified.scalar() or 0,
            "unverified_users": (total.scalar() or 0) - (verified.scalar() or 0),
            "users_by_role": by_role,
            "users_by_department": by_department,
        }

    # Session management
    async def create_session(
        self,
        user_id: UUID,
        refresh_token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> UserSession:
        """Create a new user session."""
        session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_session_by_token(
        self,
        refresh_token: str,
    ) -> Optional[UserSession]:
        """Get session by refresh token."""
        query = select(UserSession).where(
            and_(
                UserSession.refresh_token == refresh_token,
                UserSession.is_active == True,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        user_id: UUID,
        active_only: bool = True,
    ) -> Sequence[UserSession]:
        """Get all sessions for a user."""
        query = select(UserSession).where(UserSession.user_id == user_id)

        if active_only:
            query = query.where(UserSession.is_active == True)

        query = query.order_by(UserSession.last_activity.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_session_activity(
        self,
        session_id: UUID,
    ) -> None:
        """Update session's last activity timestamp."""
        await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_activity=datetime.utcnow())
        )
        await self.db.flush()

    async def revoke_session(
        self,
        session_id: UUID,
    ) -> bool:
        """Revoke a specific session."""
        result = await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_active=False)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def revoke_all_sessions(
        self,
        user_id: UUID,
        except_session_id: Optional[UUID] = None,
    ) -> int:
        """Revoke all sessions for a user."""
        query = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)
        )

        if except_session_id:
            query = query.where(UserSession.id != except_session_id)

        query = query.values(is_active=False)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount

    # Profile image management
    async def get_profile_image(
        self,
        user_id: UUID,
    ) -> Optional[ProfileImage]:
        """Get active profile image for a user."""
        query = select(ProfileImage).where(
            and_(
                ProfileImage.user_id == user_id,
                ProfileImage.is_active == True,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_profile_image(
        self,
        user_id: UUID,
        file_path: str,
        file_name: str,
        mime_type: str,
        file_size: int,
    ) -> ProfileImage:
        """Create a profile image record."""
        # Deactivate existing images
        await self.db.execute(
            update(ProfileImage)
            .where(ProfileImage.user_id == user_id)
            .values(is_active=False)
        )

        # Create new image
        image = ProfileImage(
            user_id=user_id,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            is_active=True,
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image
