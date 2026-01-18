"""Room and bed repository."""

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.enums import BedStatus, RoomType
from app.db.models.room import Room, Bed
from .base import BaseRepository


class RoomRepository(BaseRepository[Room]):
    """Repository for Room model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Room, db)

    async def get_by_room_number(
        self,
        room_number: str,
        branch_id: UUID,
    ) -> Optional[Room]:
        """Get room by number and branch."""
        query = select(Room).where(
            and_(
                Room.room_number == room_number,
                Room.branch_id == branch_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_beds(self, id: UUID) -> Optional[Room]:
        """Get room with beds."""
        query = (
            select(Room)
            .where(Room.id == id)
            .options(selectinload(Room.beds))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_rooms_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        branch_id: Optional[UUID] = None,
        room_type: Optional[RoomType] = None,
        floor: Optional[int] = None,
        building: Optional[str] = None,
        has_available_beds: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[Room]:
        """Get list of rooms with filters."""
        query = select(Room).options(selectinload(Room.beds))

        conditions = []

        if branch_id:
            conditions.append(Room.branch_id == branch_id)
        if room_type:
            conditions.append(Room.room_type == room_type)
        if floor is not None:
            conditions.append(Room.floor == floor)
        if building:
            conditions.append(Room.building == building)
        if is_active is not None:
            conditions.append(Room.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Room.room_number)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        rooms = result.unique().scalars().all()

        # Filter by available beds if requested
        if has_available_beds is not None:
            filtered_rooms = []
            for room in rooms:
                available = sum(
                    1 for bed in room.beds
                    if bed.is_active and bed.status == BedStatus.AVAILABLE
                )
                if has_available_beds and available > 0:
                    filtered_rooms.append(room)
                elif not has_available_beds and available == 0:
                    filtered_rooms.append(room)
            return filtered_rooms

        return rooms

    async def get_available_rooms(
        self,
        branch_id: UUID,
        room_type: Optional[RoomType] = None,
    ) -> Sequence[Room]:
        """Get rooms with available beds."""
        query = (
            select(Room)
            .where(
                and_(
                    Room.branch_id == branch_id,
                    Room.is_active == True,
                )
            )
            .options(selectinload(Room.beds))
        )

        if room_type:
            query = query.where(Room.room_type == room_type)

        result = await self.db.execute(query)
        rooms = result.unique().scalars().all()

        # Filter rooms that have at least one available bed
        return [
            room for room in rooms
            if any(
                bed.is_active and bed.status == BedStatus.AVAILABLE
                for bed in room.beds
            )
        ]


class BedRepository(BaseRepository[Bed]):
    """Repository for Bed model."""

    def __init__(self, db: AsyncSession):
        super().__init__(Bed, db)

    async def get_by_bed_number(
        self,
        bed_number: str,
        room_id: UUID,
    ) -> Optional[Bed]:
        """Get bed by number and room."""
        query = select(Bed).where(
            and_(
                Bed.bed_number == bed_number,
                Bed.room_id == room_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_room(self, id: UUID) -> Optional[Bed]:
        """Get bed with room details."""
        query = (
            select(Bed)
            .where(Bed.id == id)
            .options(joinedload(Bed.room))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_beds_list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        room_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        status: Optional[BedStatus] = None,
        room_type: Optional[RoomType] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[Bed]:
        """Get list of beds with filters."""
        query = select(Bed).join(Room).options(joinedload(Bed.room))

        conditions = []

        if room_id:
            conditions.append(Bed.room_id == room_id)
        if branch_id:
            conditions.append(Room.branch_id == branch_id)
        if status:
            conditions.append(Bed.status == status)
        if room_type:
            conditions.append(Room.room_type == room_type)
        if is_active is not None:
            conditions.append(Bed.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Room.room_number, Bed.bed_number)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def get_available_beds(
        self,
        branch_id: UUID,
        room_type: Optional[RoomType] = None,
    ) -> Sequence[Bed]:
        """Get available beds."""
        query = (
            select(Bed)
            .join(Room)
            .where(
                and_(
                    Room.branch_id == branch_id,
                    Room.is_active == True,
                    Bed.is_active == True,
                    Bed.status == BedStatus.AVAILABLE,
                )
            )
            .options(joinedload(Bed.room))
        )

        if room_type:
            query = query.where(Room.room_type == room_type)

        query = query.order_by(Room.room_number, Bed.bed_number)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        bed_id: UUID,
        status: BedStatus,
        current_patient_id: Optional[UUID] = None,
    ) -> bool:
        """Update bed status."""
        result = await self.db.execute(
            update(Bed)
            .where(Bed.id == bed_id)
            .values(
                status=status,
                current_patient_id=current_patient_id,
            )
        )
        await self.db.flush()
        return result.rowcount > 0

    async def assign_patient(
        self,
        bed_id: UUID,
        patient_id: UUID,
    ) -> bool:
        """Assign patient to bed."""
        return await self.update_status(
            bed_id,
            BedStatus.OCCUPIED,
            patient_id,
        )

    async def release_bed(
        self,
        bed_id: UUID,
        for_cleaning: bool = True,
    ) -> bool:
        """Release bed (optionally mark for cleaning)."""
        status = BedStatus.CLEANING if for_cleaning else BedStatus.AVAILABLE
        return await self.update_status(bed_id, status, None)

    async def get_bed_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get bed statistics."""
        query_base = select(func.count(Bed.id)).join(Room).where(Bed.is_active == True)

        if branch_id:
            query_base = query_base.where(Room.branch_id == branch_id)

        # Total beds
        total = await self.db.execute(query_base)

        # By status
        status_query = (
            select(Bed.status, func.count(Bed.id))
            .join(Room)
            .where(Bed.is_active == True)
            .group_by(Bed.status)
        )
        if branch_id:
            status_query = status_query.where(Room.branch_id == branch_id)
        status_result = await self.db.execute(status_query)
        by_status = {str(s.value): c for s, c in status_result.all()}

        # By room type
        type_query = (
            select(Room.room_type, func.count(Bed.id))
            .join(Room)
            .where(Bed.is_active == True)
            .group_by(Room.room_type)
        )
        if branch_id:
            type_query = type_query.where(Room.branch_id == branch_id)
        type_result = await self.db.execute(type_query)
        by_room_type = {str(t.value): c for t, c in type_result.all()}

        total_count = total.scalar() or 0
        available = by_status.get("available", 0)
        occupied = by_status.get("occupied", 0)
        occupancy_rate = (occupied / total_count * 100) if total_count > 0 else 0

        return {
            "total_beds": total_count,
            "available_beds": available,
            "occupied_beds": occupied,
            "under_maintenance_beds": by_status.get("under_maintenance", 0),
            "cleaning_beds": by_status.get("cleaning", 0),
            "occupancy_rate": round(occupancy_rate, 2),
            "by_status": by_status,
            "by_room_type": by_room_type,
        }
