"""
Room and bed management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.room import (
    RoomCreate,
    RoomUpdate,
    RoomResponse,
    RoomListResponse,
    RoomDetailResponse,
    RoomFilter,
    BedCreate,
    BedUpdate,
    BedResponse,
    BedAssignmentRequest,
    BedTransferRequest,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.room import RoomService
from app.models.user import User
from app.models.enums import RoomType, RoomStatus, BedStatus

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=RoomListResponse)
@require_permissions(Permission.VIEW_ROOM)
async def list_rooms(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    room_type: Optional[RoomType] = None,
    status: Optional[RoomStatus] = None,
    floor: Optional[int] = None,
):
    """
    List rooms with filtering and pagination.

    Requires: VIEW_ROOM permission
    """
    room_service = RoomService(db)

    filters = RoomFilter(
        branch_id=branch_id,
        room_type=room_type,
        status=status,
        floor=floor,
    )

    rooms = await room_service.get_rooms(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await room_service.count_rooms(filters=filters)

    return RoomListResponse(
        items=[RoomResponse.model_validate(r) for r in rooms],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/available")
@require_permissions(Permission.VIEW_ROOM)
async def get_available_rooms(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
    room_type: Optional[RoomType] = None,
):
    """
    Get rooms with available beds.

    Requires: VIEW_ROOM permission
    """
    room_service = RoomService(db)

    rooms = await room_service.get_available_rooms(
        branch_id=branch_id,
        room_type=room_type,
    )

    return {"rooms": [RoomResponse.model_validate(r) for r in rooms]}


@router.get("/occupancy")
@require_permissions(Permission.VIEW_ROOM)
async def get_occupancy_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
):
    """
    Get room occupancy statistics.

    Requires: VIEW_ROOM permission
    """
    room_service = RoomService(db)
    stats = await room_service.get_occupancy_stats(branch_id)
    return stats


@router.get("/{room_id}", response_model=RoomDetailResponse)
@require_permissions(Permission.VIEW_ROOM)
async def get_room(
    room_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific room by ID.

    Requires: VIEW_ROOM permission
    """
    room_service = RoomService(db)

    try:
        room = await room_service.get_room(room_id)
        return RoomDetailResponse.model_validate(room)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )


@router.get("/{room_id}/beds", response_model=list[BedResponse])
@require_permissions(Permission.VIEW_ROOM)
async def get_room_beds(
    room_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get all beds in a room.

    Requires: VIEW_ROOM permission
    """
    room_service = RoomService(db)

    try:
        beds = await room_service.get_room_beds(room_id)
        return [BedResponse.model_validate(b) for b in beds]
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_ROOM)
async def create_room(
    room_data: RoomCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new room.

    Requires: CREATE_ROOM permission
    """
    room_service = RoomService(db)

    try:
        room = await room_service.create_room(
            created_by=current_user.id,
            **room_data.model_dump(),
        )
        return RoomResponse.model_validate(room)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{room_id}", response_model=RoomResponse)
@require_permissions(Permission.UPDATE_ROOM)
async def update_room(
    room_id: UUID,
    room_data: RoomUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a room.

    Requires: UPDATE_ROOM permission
    """
    room_service = RoomService(db)

    try:
        room = await room_service.update_room(
            room_id=room_id,
            **room_data.model_dump(exclude_unset=True),
        )
        return RoomResponse.model_validate(room)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{room_id}/beds", response_model=BedResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.UPDATE_ROOM)
async def add_bed_to_room(
    room_id: UUID,
    bed_data: BedCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add a bed to a room.

    Requires: UPDATE_ROOM permission
    """
    room_service = RoomService(db)

    try:
        bed = await room_service.add_bed(
            room_id=room_id,
            **bed_data.model_dump(),
        )
        return BedResponse.model_validate(bed)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/beds/{bed_id}", response_model=BedResponse)
@require_permissions(Permission.UPDATE_ROOM)
async def update_bed(
    bed_id: UUID,
    bed_data: BedUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a bed.

    Requires: UPDATE_ROOM permission
    """
    room_service = RoomService(db)

    try:
        bed = await room_service.update_bed(
            bed_id=bed_id,
            **bed_data.model_dump(exclude_unset=True),
        )
        return BedResponse.model_validate(bed)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bed not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/beds/{bed_id}/assign", response_model=SuccessResponse)
@require_permissions(Permission.ASSIGN_BED)
async def assign_bed(
    bed_id: UUID,
    assignment: BedAssignmentRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Assign a bed to a patient/admission.

    Requires: ASSIGN_BED permission
    """
    room_service = RoomService(db)

    try:
        await room_service.assign_bed(
            bed_id=bed_id,
            admission_id=assignment.admission_id,
            assigned_by=current_user.id,
        )
        return SuccessResponse(message="Bed assigned successfully")
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/beds/{bed_id}/release", response_model=SuccessResponse)
@require_permissions(Permission.ASSIGN_BED)
async def release_bed(
    bed_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Release a bed (mark as available).

    Requires: ASSIGN_BED permission
    """
    room_service = RoomService(db)

    try:
        await room_service.release_bed(bed_id)
        return SuccessResponse(message="Bed released successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bed not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/beds/transfer", response_model=SuccessResponse)
@require_permissions(Permission.ASSIGN_BED)
async def transfer_bed(
    transfer_data: BedTransferRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Transfer a patient from one bed to another.

    Requires: ASSIGN_BED permission
    """
    room_service = RoomService(db)

    try:
        await room_service.transfer_bed(
            from_bed_id=transfer_data.from_bed_id,
            to_bed_id=transfer_data.to_bed_id,
            reason=transfer_data.reason,
            transferred_by=current_user.id,
        )
        return SuccessResponse(message="Bed transfer completed successfully")
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/beds/{bed_id}", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_ROOM)
async def delete_bed(
    bed_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a bed.

    Requires: UPDATE_ROOM permission
    """
    room_service = RoomService(db)

    try:
        await room_service.delete_bed(bed_id)
        return SuccessResponse(message="Bed deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bed not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{room_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_ROOM)
async def delete_room(
    room_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a room.

    Requires: DELETE_ROOM permission
    """
    room_service = RoomService(db)

    try:
        await room_service.delete_room(room_id)
        return SuccessResponse(message="Room deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
