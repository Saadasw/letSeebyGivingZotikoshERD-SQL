"""Room and bed service."""

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.models.enums import BedStatus, RoomType
from app.db.models.room import Room, Bed
from app.repositories.room import RoomRepository, BedRepository


class RoomService:
    """Room and bed management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.room_repo = RoomRepository(db)
        self.bed_repo = BedRepository(db)

    # Rooms
    async def get_room(self, room_id: UUID) -> Optional[Room]:
        """Get room by ID."""
        return await self.room_repo.get_with_beds(room_id)

    async def get_room_by_number(
        self,
        room_number: str,
        branch_id: UUID,
    ) -> Optional[Room]:
        """Get room by number and branch."""
        return await self.room_repo.get_by_room_number(room_number, branch_id)

    async def get_rooms(
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
        """Get list of rooms."""
        return await self.room_repo.get_rooms_list(
            skip=skip,
            limit=limit,
            branch_id=branch_id,
            room_type=room_type,
            floor=floor,
            building=building,
            has_available_beds=has_available_beds,
            is_active=is_active,
        )

    async def create_room(
        self,
        branch_id: UUID,
        room_number: str,
        room_type: RoomType,
        **room_data,
    ) -> Room:
        """Create a new room."""
        # Check if room number exists in branch
        existing = await self.room_repo.get_by_room_number(room_number, branch_id)
        if existing:
            raise ConflictError("Room number already exists in this branch")

        room = await self.room_repo.create({
            "branch_id": branch_id,
            "room_number": room_number,
            "room_type": room_type,
            **room_data,
        })

        await self.db.commit()
        await self.db.refresh(room)

        return room

    async def update_room(
        self,
        room_id: UUID,
        **update_data,
    ) -> Optional[Room]:
        """Update room."""
        room = await self.room_repo.get(room_id)
        if not room:
            raise NotFoundError("Room not found")

        # Check room number uniqueness if updating
        if "room_number" in update_data and update_data["room_number"] != room.room_number:
            existing = await self.room_repo.get_by_room_number(
                update_data["room_number"], room.branch_id
            )
            if existing:
                raise ConflictError("Room number already in use")

        updated = await self.room_repo.update(room_id, update_data)
        await self.db.commit()

        return updated

    async def get_available_rooms(
        self,
        branch_id: UUID,
        room_type: Optional[RoomType] = None,
    ) -> Sequence[Room]:
        """Get rooms with available beds."""
        return await self.room_repo.get_available_rooms(branch_id, room_type)

    # Beds
    async def get_bed(self, bed_id: UUID) -> Optional[Bed]:
        """Get bed by ID."""
        return await self.bed_repo.get_with_room(bed_id)

    async def get_bed_by_number(
        self,
        bed_number: str,
        room_id: UUID,
    ) -> Optional[Bed]:
        """Get bed by number and room."""
        return await self.bed_repo.get_by_bed_number(bed_number, room_id)

    async def get_beds(
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
        """Get list of beds."""
        return await self.bed_repo.get_beds_list(
            skip=skip,
            limit=limit,
            room_id=room_id,
            branch_id=branch_id,
            status=status,
            room_type=room_type,
            is_active=is_active,
        )

    async def create_bed(
        self,
        room_id: UUID,
        bed_number: str,
        **bed_data,
    ) -> Bed:
        """Create a new bed."""
        # Check room exists
        room = await self.room_repo.get(room_id)
        if not room:
            raise NotFoundError("Room not found")

        # Check if bed number exists in room
        existing = await self.bed_repo.get_by_bed_number(bed_number, room_id)
        if existing:
            raise ConflictError("Bed number already exists in this room")

        bed = await self.bed_repo.create({
            "room_id": room_id,
            "bed_number": bed_number,
            "status": BedStatus.AVAILABLE,
            **bed_data,
        })

        await self.db.commit()
        await self.db.refresh(bed)

        return bed

    async def update_bed(
        self,
        bed_id: UUID,
        **update_data,
    ) -> Optional[Bed]:
        """Update bed."""
        bed = await self.bed_repo.get(bed_id)
        if not bed:
            raise NotFoundError("Bed not found")

        # Check bed number uniqueness if updating
        if "bed_number" in update_data and update_data["bed_number"] != bed.bed_number:
            existing = await self.bed_repo.get_by_bed_number(
                update_data["bed_number"], bed.room_id
            )
            if existing:
                raise ConflictError("Bed number already in use")

        updated = await self.bed_repo.update(bed_id, update_data)
        await self.db.commit()

        return updated

    async def get_available_beds(
        self,
        branch_id: UUID,
        room_type: Optional[RoomType] = None,
    ) -> Sequence[Bed]:
        """Get available beds."""
        return await self.bed_repo.get_available_beds(branch_id, room_type)

    async def assign_patient_to_bed(
        self,
        bed_id: UUID,
        patient_id: UUID,
    ) -> bool:
        """Assign patient to a bed."""
        bed = await self.bed_repo.get(bed_id)
        if not bed:
            raise NotFoundError("Bed not found")

        if bed.status != BedStatus.AVAILABLE:
            raise ValidationError("Bed is not available")

        result = await self.bed_repo.assign_patient(bed_id, patient_id)
        await self.db.commit()

        return result

    async def release_bed(
        self,
        bed_id: UUID,
        for_cleaning: bool = True,
    ) -> bool:
        """Release a bed."""
        bed = await self.bed_repo.get(bed_id)
        if not bed:
            raise NotFoundError("Bed not found")

        if bed.status not in [BedStatus.OCCUPIED, BedStatus.RESERVED]:
            raise ValidationError("Bed is not occupied or reserved")

        result = await self.bed_repo.release_bed(bed_id, for_cleaning)
        await self.db.commit()

        return result

    async def mark_bed_available(self, bed_id: UUID) -> bool:
        """Mark bed as available (after cleaning)."""
        result = await self.bed_repo.update_status(bed_id, BedStatus.AVAILABLE)
        await self.db.commit()
        return result

    async def mark_bed_under_maintenance(
        self,
        bed_id: UUID,
    ) -> bool:
        """Mark bed as under maintenance."""
        result = await self.bed_repo.update_status(bed_id, BedStatus.UNDER_MAINTENANCE)
        await self.db.commit()
        return result

    async def transfer_patient(
        self,
        from_bed_id: UUID,
        to_bed_id: UUID,
    ) -> bool:
        """Transfer patient from one bed to another."""
        from_bed = await self.bed_repo.get(from_bed_id)
        to_bed = await self.bed_repo.get(to_bed_id)

        if not from_bed or not to_bed:
            raise NotFoundError("Bed not found")

        if from_bed.status != BedStatus.OCCUPIED:
            raise ValidationError("Source bed is not occupied")

        if to_bed.status != BedStatus.AVAILABLE:
            raise ValidationError("Target bed is not available")

        patient_id = from_bed.current_patient_id

        # Release old bed
        await self.bed_repo.release_bed(from_bed_id, for_cleaning=True)

        # Assign new bed
        await self.bed_repo.assign_patient(to_bed_id, patient_id)

        await self.db.commit()
        return True

    async def get_bed_stats(
        self,
        branch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Get bed statistics."""
        return await self.bed_repo.get_bed_stats(branch_id)
