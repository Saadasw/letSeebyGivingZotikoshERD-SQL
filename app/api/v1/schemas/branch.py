"""Branch schemas."""

from datetime import time
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from .base import BaseSchema, IDTimestampSchema, AddressSchema


# ==========================================
# BRANCH
# ==========================================


class BranchBase(BaseSchema):
    """Base branch schema."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None


class BranchAddressInfo(AddressSchema):
    """Branch address info."""

    pass


class BranchCreate(BranchBase, BranchAddressInfo):
    """Create branch schema."""

    pass


class BranchUpdate(BaseSchema):
    """Update branch schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class BranchResponse(IDTimestampSchema, BranchBase, BranchAddressInfo):
    """Branch response schema."""

    is_active: bool
    is_main: bool


class BranchListResponse(BaseSchema):
    """Branch list item (minimal)."""

    id: UUID
    name: str
    code: str
    city: Optional[str] = None
    is_active: bool
    is_main: bool


class BranchDetailResponse(BranchResponse):
    """Detailed branch response."""

    total_doctors: int = 0
    total_staff: int = 0
    total_rooms: int = 0
    total_beds: int = 0
    available_beds: int = 0


# ==========================================
# BRANCH FILTERS
# ==========================================


class BranchFilterParams(BaseSchema):
    """Branch filter parameters."""

    search: Optional[str] = Field(None, description="Search in name or code")
    city: Optional[str] = None
    state: Optional[str] = None
    is_active: Optional[bool] = None


# ==========================================
# BRANCH STATISTICS
# ==========================================


class BranchStatsResponse(BaseSchema):
    """Branch statistics response."""

    total_branches: int
    active_branches: int
    total_doctors: int
    total_staff: int
    total_rooms: int
    total_beds: int
    available_beds: int
    occupancy_rate: float = 0.0
