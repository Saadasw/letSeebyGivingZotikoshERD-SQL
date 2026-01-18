"""Branch repository."""

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.branch import Branch
from .base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    """Repository for Branch model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Branch, db)

    async def get_by_code(self, code: str) -> Optional[Branch]:
        """Get branch by code."""
        query = select(Branch).where(Branch.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_main_branch(self) -> Optional[Branch]:
        """Get the main branch."""
        query = select(Branch).where(Branch.is_main == True)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_branches_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[Branch]:
        """Get list of branches with filters."""
        query = select(Branch)

        conditions = []

        if search:
            conditions.append(
                or_(
                    Branch.name.ilike(f"%{search}%"),
                    Branch.code.ilike(f"%{search}%"),
                )
            )

        if city:
            conditions.append(Branch.city.ilike(f"%{city}%"))

        if state:
            conditions.append(Branch.state.ilike(f"%{state}%"))

        if is_active is not None:
            conditions.append(Branch.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Branch.is_main.desc(), Branch.name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_branches(
        self,
        *,
        city: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count branches matching filters."""
        query = select(func.count(Branch.id))

        conditions = []

        if city:
            conditions.append(Branch.city.ilike(f"%{city}%"))

        if is_active is not None:
            conditions.append(Branch.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_branch_with_stats(self, branch_id: UUID) -> Optional[dict[str, Any]]:
        """Get branch with related statistics."""
        branch = await self.get(branch_id)
        if not branch:
            return None

        # Import here to avoid circular imports
        from app.db.models.doctor import DoctorBranchAssignment
        from app.db.models.staff import StaffProfile
        from app.db.models.room import Room, Bed
        from app.db.models.enums import BedStatus

        # Count doctors
        doctor_query = select(func.count(DoctorBranchAssignment.id)).where(
            DoctorBranchAssignment.branch_id == branch_id
        )
        doctor_count = await self.db.execute(doctor_query)

        # Count staff
        staff_query = select(func.count(StaffProfile.id)).where(
            and_(
                StaffProfile.branch_id == branch_id,
                StaffProfile.is_active == True,
            )
        )
        staff_count = await self.db.execute(staff_query)

        # Count rooms and beds
        room_query = select(func.count(Room.id)).where(
            and_(
                Room.branch_id == branch_id,
                Room.is_active == True,
            )
        )
        room_count = await self.db.execute(room_query)

        bed_query = select(func.count(Bed.id)).where(
            and_(
                Bed.room_id.in_(
                    select(Room.id).where(Room.branch_id == branch_id)
                ),
                Bed.is_active == True,
            )
        )
        bed_count = await self.db.execute(bed_query)

        available_bed_query = select(func.count(Bed.id)).where(
            and_(
                Bed.room_id.in_(
                    select(Room.id).where(Room.branch_id == branch_id)
                ),
                Bed.is_active == True,
                Bed.status == BedStatus.AVAILABLE,
            )
        )
        available_bed_count = await self.db.execute(available_bed_query)

        return {
            "branch": branch,
            "total_doctors": doctor_count.scalar() or 0,
            "total_staff": staff_count.scalar() or 0,
            "total_rooms": room_count.scalar() or 0,
            "total_beds": bed_count.scalar() or 0,
            "available_beds": available_bed_count.scalar() or 0,
        }

    async def get_branch_stats(self) -> dict[str, Any]:
        """Get overall branch statistics."""
        from app.db.models.room import Room, Bed
        from app.db.models.enums import BedStatus

        # Total branches
        total_query = select(func.count(Branch.id))
        total = await self.db.execute(total_query)

        # Active branches
        active_query = select(func.count(Branch.id)).where(Branch.is_active == True)
        active = await self.db.execute(active_query)

        # Total beds across all branches
        bed_query = select(func.count(Bed.id)).where(Bed.is_active == True)
        total_beds = await self.db.execute(bed_query)

        # Available beds
        available_query = select(func.count(Bed.id)).where(
            and_(
                Bed.is_active == True,
                Bed.status == BedStatus.AVAILABLE,
            )
        )
        available_beds = await self.db.execute(available_query)

        total_beds_count = total_beds.scalar() or 0
        available_beds_count = available_beds.scalar() or 0
        occupancy_rate = 0.0
        if total_beds_count > 0:
            occupancy_rate = ((total_beds_count - available_beds_count) / total_beds_count) * 100

        return {
            "total_branches": total.scalar() or 0,
            "active_branches": active.scalar() or 0,
            "total_beds": total_beds_count,
            "available_beds": available_beds_count,
            "occupancy_rate": round(occupancy_rate, 2),
        }
