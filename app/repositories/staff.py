"""Staff repository."""

from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.enums import StaffDepartment
from app.db.models.staff import StaffProfile
from app.db.models.user import User
from .base import BaseRepository


class StaffRepository(BaseRepository[StaffProfile]):
    """Repository for StaffProfile model."""

    def __init__(self, db: AsyncSession):
        super().__init__(StaffProfile, db)

    async def get_by_user_id(self, user_id: UUID) -> Optional[StaffProfile]:
        """Get staff profile by user ID."""
        query = (
            select(StaffProfile)
            .where(StaffProfile.user_id == user_id)
            .options(joinedload(StaffProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_staff_id(self, staff_id: str) -> Optional[StaffProfile]:
        """Get staff profile by auto-generated staff ID."""
        query = (
            select(StaffProfile)
            .where(StaffProfile.staff_id == staff_id)
            .options(joinedload(StaffProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, employee_id: str) -> Optional[StaffProfile]:
        """Get staff profile by employee ID."""
        query = (
            select(StaffProfile)
            .where(StaffProfile.employee_id == employee_id)
            .options(joinedload(StaffProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_user(self, id: UUID) -> Optional[StaffProfile]:
        """Get staff profile with user details."""
        query = (
            select(StaffProfile)
            .where(StaffProfile.id == id)
            .options(joinedload(StaffProfile.user))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

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
        query = (
            select(StaffProfile)
            .join(User)
            .options(joinedload(StaffProfile.user))
        )

        conditions = []

        if search:
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    StaffProfile.staff_id.ilike(f"%{search}%"),
                    StaffProfile.employee_id.ilike(f"%{search}%"),
                )
            )

        if department:
            conditions.append(StaffProfile.department == department)

        if branch_id:
            conditions.append(StaffProfile.branch_id == branch_id)

        if position:
            conditions.append(StaffProfile.position.ilike(f"%{position}%"))

        if is_active is not None:
            conditions.append(StaffProfile.is_active == is_active)
            conditions.append(User.is_active == is_active)

        if hired_after:
            conditions.append(StaffProfile.hire_date >= hired_after)

        if hired_before:
            conditions.append(StaffProfile.hire_date <= hired_before)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(StaffProfile.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_staff(
        self,
        *,
        department: Optional[StaffDepartment] = None,
        branch_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count staff matching filters."""
        query = select(func.count(StaffProfile.id)).join(User)

        conditions = []

        if department:
            conditions.append(StaffProfile.department == department)

        if branch_id:
            conditions.append(StaffProfile.branch_id == branch_id)

        if is_active is not None:
            conditions.append(StaffProfile.is_active == is_active)
            conditions.append(User.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_by_department(
        self,
        department: StaffDepartment,
        *,
        branch_id: Optional[UUID] = None,
        active_only: bool = True,
    ) -> Sequence[StaffProfile]:
        """Get staff by department."""
        query = (
            select(StaffProfile)
            .where(StaffProfile.department == department)
            .join(User)
            .options(joinedload(StaffProfile.user))
        )

        if branch_id:
            query = query.where(StaffProfile.branch_id == branch_id)

        if active_only:
            query = query.where(
                and_(
                    StaffProfile.is_active == True,
                    User.is_active == True,
                )
            )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_branch(
        self,
        branch_id: UUID,
        *,
        department: Optional[StaffDepartment] = None,
        active_only: bool = True,
    ) -> Sequence[StaffProfile]:
        """Get staff by branch."""
        query = (
            select(StaffProfile)
            .where(StaffProfile.branch_id == branch_id)
            .join(User)
            .options(joinedload(StaffProfile.user))
        )

        if department:
            query = query.where(StaffProfile.department == department)

        if active_only:
            query = query.where(
                and_(
                    StaffProfile.is_active == True,
                    User.is_active == True,
                )
            )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_staff_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get staff statistics."""
        base_query = select(func.count(StaffProfile.id))

        if branch_id:
            base_query = base_query.where(StaffProfile.branch_id == branch_id)

        # Total staff
        total = await self.db.execute(base_query)

        # Active staff
        active_query = base_query.where(StaffProfile.is_active == True)
        active = await self.db.execute(active_query)

        # By department
        dept_query = (
            select(StaffProfile.department, func.count(StaffProfile.id))
            .group_by(StaffProfile.department)
        )
        if branch_id:
            dept_query = dept_query.where(StaffProfile.branch_id == branch_id)
        dept_result = await self.db.execute(dept_query)
        by_department = {str(d.value): c for d, c in dept_result.all()}

        # By branch
        branch_query = (
            select(StaffProfile.branch_id, func.count(StaffProfile.id))
            .group_by(StaffProfile.branch_id)
        )
        branch_result = await self.db.execute(branch_query)
        by_branch = {str(b): c for b, c in branch_result.all()}

        return {
            "total_staff": total.scalar() or 0,
            "active_staff": active.scalar() or 0,
            "by_department": by_department,
            "by_branch": by_branch,
        }
