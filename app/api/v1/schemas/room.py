"""Room and bed schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import BedStatus, RoomType
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# ROOM
# ==========================================


class RoomBase(BaseSchema):
    """Base room schema."""

    room_number: str = Field(..., max_length=20)
    room_type: RoomType
    floor: int = Field(1, ge=0)
    building: Optional[str] = Field(None, max_length=100)
    daily_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    description: Optional[str] = None
    amenities: Optional[str] = None


class RoomCreate(RoomBase):
    """Create room schema."""

    branch_id: UUID


class RoomUpdate(BaseSchema):
    """Update room schema."""

    room_number: Optional[str] = Field(None, max_length=20)
    room_type: Optional[RoomType] = None
    floor: Optional[int] = Field(None, ge=0)
    building: Optional[str] = Field(None, max_length=100)
    daily_rate: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    amenities: Optional[str] = None
    is_active: Optional[bool] = None


class RoomResponse(IDTimestampSchema, RoomBase):
    """Room response schema."""

    branch_id: UUID
    is_active: bool
    # Joined fields
    branch_name: Optional[str] = None


class RoomListResponse(BaseSchema):
    """Room list item."""

    id: UUID
    room_number: str
    room_type: RoomType
    floor: int
    branch_id: UUID
    branch_name: Optional[str] = None
    daily_rate: Decimal
    is_active: bool
    total_beds: int = 0
    available_beds: int = 0


class RoomDetailResponse(RoomResponse):
    """Detailed room response."""

    beds: list["BedResponse"] = []
    total_beds: int = 0
    available_beds: int = 0
    occupied_beds: int = 0


# ==========================================
# BED
# ==========================================


class BedBase(BaseSchema):
    """Base bed schema."""

    bed_number: str = Field(..., max_length=20)
    bed_type: Optional[str] = Field(None, max_length=100)
    features: Optional[str] = None


class BedCreate(BedBase):
    """Create bed schema."""

    room_id: UUID


class BedUpdate(BaseSchema):
    """Update bed schema."""

    bed_number: Optional[str] = Field(None, max_length=20)
    bed_type: Optional[str] = Field(None, max_length=100)
    features: Optional[str] = None
    status: Optional[BedStatus] = None
    is_active: Optional[bool] = None


class BedResponse(IDTimestampSchema, BedBase):
    """Bed response schema."""

    room_id: UUID
    status: BedStatus
    is_active: bool
    current_patient_id: Optional[UUID] = None
    # Joined fields
    room_number: Optional[str] = None
    room_type: Optional[RoomType] = None


class BedListResponse(BaseSchema):
    """Bed list item."""

    id: UUID
    bed_number: str
    room_id: UUID
    room_number: str
    room_type: RoomType
    status: BedStatus
    is_active: bool
    current_patient_name: Optional[str] = None


class BedDetailResponse(BedResponse):
    """Detailed bed response."""

    room: Optional[RoomResponse] = None
    current_patient_name: Optional[str] = None
    current_admission_id: Optional[UUID] = None


# ==========================================
# BED ASSIGNMENT
# ==========================================


class BedAssignmentRequest(BaseSchema):
    """Bed assignment request."""

    bed_id: UUID
    patient_id: UUID
    admission_id: Optional[UUID] = None
    notes: Optional[str] = None


class BedReleaseRequest(BaseSchema):
    """Bed release request."""

    bed_id: UUID
    reason: Optional[str] = None
    cleaning_required: bool = True


class BedTransferRequest(BaseSchema):
    """Bed transfer request."""

    from_bed_id: UUID
    to_bed_id: UUID
    reason: Optional[str] = None


# ==========================================
# ROOM/BED FILTERS
# ==========================================


class RoomFilterParams(BaseSchema):
    """Room filter parameters."""

    branch_id: Optional[UUID] = None
    room_type: Optional[RoomType] = None
    floor: Optional[int] = None
    building: Optional[str] = None
    has_available_beds: Optional[bool] = None
    min_rate: Optional[Decimal] = None
    max_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None


class BedFilterParams(BaseSchema):
    """Bed filter parameters."""

    room_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    status: Optional[BedStatus] = None
    room_type: Optional[RoomType] = None
    is_active: Optional[bool] = None


# ==========================================
# ROOM STATISTICS
# ==========================================


class RoomStatsResponse(BaseSchema):
    """Room statistics response."""

    total_rooms: int
    active_rooms: int
    total_beds: int
    available_beds: int
    occupied_beds: int
    under_maintenance_beds: int
    cleaning_beds: int
    occupancy_rate: float = 0.0
    by_room_type: dict[str, dict[str, int]]
    by_branch: dict[str, dict[str, int]]


class BedOccupancyReport(BaseSchema):
    """Bed occupancy report."""

    branch_id: UUID
    branch_name: str
    total_beds: int
    occupied: int
    available: int
    under_maintenance: int
    occupancy_rate: float


# Forward references
RoomDetailResponse.model_rebuild()
