"""User service."""

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.db.models.enums import UserRole, StaffDepartment
from app.db.models.user import User
from app.repositories.user import UserRepository


class UserService:
    """User management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repo.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.user_repo.get_by_email(email)

    async def get_user_with_profile(self, user_id: UUID) -> Optional[User]:
        """Get user with related profile."""
        return await self.user_repo.get_with_profile(user_id)

    async def get_users(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        department: Optional[StaffDepartment] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[User]:
        """Get list of users with filters."""
        if search:
            return await self.user_repo.search_users(
                search,
                skip=skip,
                limit=limit,
                role=role,
                department=department,
                is_active=is_active,
            )

        filters = {}
        if role:
            filters["role"] = role
        if department:
            filters["department"] = department
        if is_active is not None:
            filters["is_active"] = is_active

        return await self.user_repo.get_multi(
            skip=skip,
            limit=limit,
            filters=filters if filters else None,
        )

    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole,
        phone: Optional[str] = None,
        department: Optional[StaffDepartment] = None,
        branch_id: Optional[UUID] = None,
        is_active: bool = True,
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        user = await self.user_repo.create({
            "email": email,
            "hashed_password": get_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "role": role,
            "department": department,
            "branch_id": branch_id,
            "is_active": is_active,
            "is_verified": is_verified,
        })

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def update_user(
        self,
        user_id: UUID,
        **update_data,
    ) -> Optional[User]:
        """Update user."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Check email uniqueness if updating email
        if "email" in update_data and update_data["email"] != user.email:
            existing = await self.user_repo.get_by_email(update_data["email"])
            if existing:
                raise ConflictError("Email already in use")

        # Hash password if provided
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        updated = await self.user_repo.update(user_id, update_data)
        await self.db.commit()

        return updated

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Soft delete by deactivating
        await self.user_repo.update(user_id, {"is_active": False})
        await self.db.commit()

        return True

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activate user."""
        return await self.update_user(user_id, is_active=True)

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate user."""
        return await self.update_user(user_id, is_active=False)

    async def verify_user(self, user_id: UUID) -> bool:
        """Mark user as verified."""
        result = await self.user_repo.verify_email(user_id)
        if result:
            await self.db.commit()
        return result

    async def bulk_update_status(
        self,
        user_ids: list[UUID],
        is_active: bool,
    ) -> int:
        """Bulk update user status."""
        count = 0
        for user_id in user_ids:
            try:
                await self.user_repo.update(user_id, {"is_active": is_active})
                count += 1
            except Exception:
                continue

        await self.db.commit()
        return count

    async def get_user_stats(self) -> dict[str, Any]:
        """Get user statistics."""
        return await self.user_repo.get_user_stats()

    # Profile Image
    async def get_profile_image(self, user_id: UUID):
        """Get user's profile image."""
        return await self.user_repo.get_profile_image(user_id)

    async def upload_profile_image(
        self,
        user_id: UUID,
        file_path: str,
        file_name: str,
        mime_type: str,
        file_size: int,
    ):
        """Upload profile image."""
        image = await self.user_repo.create_profile_image(
            user_id=user_id,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
        )
        await self.db.commit()
        return image
