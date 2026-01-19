"""Staff service."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.db.models.enums import StaffDepartment, UserRole
from app.db.models.staff import StaffProfile
from app.repositories.staff import StaffRepository
from app.repositories.user import UserRepository


class StaffService:
    """Staff management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.staff_repo = StaffRepository(db)
        self.user_repo = UserRepository(db)

    async def get_staff(self, staff_id: UUID) -> Optional[StaffProfile]:
        """Get staff by ID."""
        return await self.staff_repo.get_with_user(staff_id)

    async def get_staff_by_user_id(self, user_id: UUID) -> Optional[StaffProfile]:
        """Get staff by user ID."""
        return await self.staff_repo.get_by_user_id(user_id)

    async def get_staff_by_staff_id(self, staff_id: str) -> Optional[StaffProfile]:
        """Get staff by auto-generated staff ID."""
        return await self.staff_repo.get_by_staff_id(staff_id)

    async def get_staff_by_employee_id(self, employee_id: str) -> Optional[StaffProfile]:
        """Get staff by employee ID."""
        return await self.staff_repo.get_by_employee_id(employee_id)

    async def get_staff_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        department: Optional[StaffDepartment] = None,
        branch_id: Optional[UUID] = None,
        position: Optional[str] = None,
        is_active: Optional[bool] = None,
        hired_after: Optional[date] = None,
        hired_before: Optional[date] = None,
    ) -> Sequence[StaffProfile]:
        """Get list of staff with filters."""
        return await self.staff_repo.get_staff_list(
            skip=skip,
            limit=limit,
            search=search,
            department=department,
            branch_id=branch_id,
            position=position,
            is_active=is_active,
            hired_after=hired_after,
            hired_before=hired_before,
        )

    async def count_staff(
        self,
        *,
        department: Optional[StaffDepartment] = None,
        branch_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count staff matching filters."""
        return await self.staff_repo.count_staff(
            department=department,
            branch_id=branch_id,
            is_active=is_active,
        )

    async def create_staff(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        department: StaffDepartment,
        position: str,
        branch_id: UUID,
        phone: Optional[str] = None,
        employee_id: Optional[str] = None,
        hire_date: Optional[date] = None,
        **staff_data,
    ) -> StaffProfile:
        """Create a new staff member with user account."""
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        # Check employee ID uniqueness
        if employee_id:
            existing_emp = await self.staff_repo.get_by_employee_id(employee_id)
            if existing_emp:
                raise ConflictError("Employee ID already in use")

        # Create user
        user = await self.user_repo.create({
            "email": email,
            "hashed_password": get_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "role": UserRole.STAFF,
            "department": department,
            "branch_id": branch_id,
            "is_active": True,
            "is_verified": True,
        })

        # Create staff profile
        staff = await self.staff_repo.create({
            "user_id": user.id,
            "department": department,
            "position": position,
            "branch_id": branch_id,
            "employee_id": employee_id,
            "hire_date": hire_date,
            **staff_data,
        })

        await self.db.commit()
        await self.db.refresh(staff)

        return staff

    async def update_staff(
        self,
        staff_id: UUID,
        **update_data,
    ) -> Optional[StaffProfile]:
        """Update staff profile."""
        staff = await self.staff_repo.get(staff_id)
        if not staff:
            raise NotFoundError("Staff not found")

        # Check employee ID uniqueness if updating
        if "employee_id" in update_data and update_data["employee_id"]:
            existing = await self.staff_repo.get_by_employee_id(update_data["employee_id"])
            if existing and existing.id != staff_id:
                raise ConflictError("Employee ID already in use")

        # Update user department if changed
        if "department" in update_data:
            await self.user_repo.update(
                staff.user_id,
                {"department": update_data["department"]},
            )

        updated = await self.staff_repo.update(staff_id, update_data)
        await self.db.commit()

        return updated

    async def deactivate_staff(self, staff_id: UUID) -> Optional[StaffProfile]:
        """Deactivate staff member."""
        staff = await self.staff_repo.get(staff_id)
        if not staff:
            raise NotFoundError("Staff not found")

        # Deactivate user
        await self.user_repo.update(staff.user_id, {"is_active": False})

        # Deactivate staff profile
        updated = await self.staff_repo.update(staff_id, {"is_active": False})
        await self.db.commit()

        return updated

    async def activate_staff(self, staff_id: UUID) -> Optional[StaffProfile]:
        """Activate staff member."""
        staff = await self.staff_repo.get(staff_id)
        if not staff:
            raise NotFoundError("Staff not found")

        # Activate user
        await self.user_repo.update(staff.user_id, {"is_active": True})

        # Activate staff profile
        updated = await self.staff_repo.update(staff_id, {"is_active": True})
        await self.db.commit()

        return updated

    async def transfer_staff(
        self,
        staff_id: UUID,
        new_branch_id: UUID,
    ) -> Optional[StaffProfile]:
        """Transfer staff to a different branch."""
        staff = await self.staff_repo.get(staff_id)
        if not staff:
            raise NotFoundError("Staff not found")

        # Update user branch
        await self.user_repo.update(staff.user_id, {"branch_id": new_branch_id})

        # Update staff profile
        updated = await self.staff_repo.update(staff_id, {"branch_id": new_branch_id})
        await self.db.commit()

        return updated

    async def get_staff_by_department(
        self,
        department: StaffDepartment,
        *,
        branch_id: Optional[UUID] = None,
        active_only: bool = True,
    ) -> Sequence[StaffProfile]:
        """Get staff by department."""
        return await self.staff_repo.get_by_department(
            department,
            branch_id=branch_id,
            active_only=active_only,
        )

    async def get_staff_by_branch(
        self,
        branch_id: UUID,
        *,
        department: Optional[StaffDepartment] = None,
        active_only: bool = True,
    ) -> Sequence[StaffProfile]:
        """Get staff by branch."""
        return await self.staff_repo.get_by_branch(
            branch_id,
            department=department,
            active_only=active_only,
        )

    async def get_staff_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get staff statistics."""
        return await self.staff_repo.get_staff_stats(branch_id)
