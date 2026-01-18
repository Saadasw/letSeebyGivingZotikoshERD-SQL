"""Base Pydantic schemas and common response models."""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema with ID field."""

    id: UUID


class IDTimestampSchema(IDSchema, TimestampSchema):
    """Schema with ID and timestamp fields."""

    pass


# ==========================================
# PAGINATION
# ==========================================

T = TypeVar("T")


class PaginationMeta(BaseSchema):
    """Pagination metadata."""

    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response."""

    items: List[T]
    meta: PaginationMeta

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
    ) -> "PaginatedResponse[T]":
        """Create paginated response from items and metadata."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )


# ==========================================
# STANDARD RESPONSES
# ==========================================


class SuccessResponse(BaseSchema):
    """Generic success response."""

    success: bool = True
    message: str = "Operation successful"
    data: Optional[Any] = None


class ErrorResponse(BaseSchema):
    """Standard error response."""

    error: str
    message: str
    details: Optional[Any] = None


class MessageResponse(BaseSchema):
    """Simple message response."""

    message: str


class DeleteResponse(BaseSchema):
    """Delete operation response."""

    success: bool = True
    message: str = "Successfully deleted"
    id: UUID


# ==========================================
# COMMON FIELD SCHEMAS
# ==========================================


class AddressSchema(BaseSchema):
    """Address fields."""

    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)


class ContactSchema(BaseSchema):
    """Contact information fields."""

    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)


class EmergencyContactSchema(BaseSchema):
    """Emergency contact fields."""

    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_relation: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


# ==========================================
# QUERY PARAMETERS
# ==========================================


class PaginationParams(BaseSchema):
    """Pagination query parameters."""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @property
    def skip(self) -> int:
        """Alias for offset."""
        return self.offset

    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size


class DateRangeParams(BaseSchema):
    """Date range query parameters."""

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SortParams(BaseSchema):
    """Sort query parameters."""

    sort_by: Optional[str] = None
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


# ==========================================
# UTILITY SCHEMAS
# ==========================================


class BulkDeleteRequest(BaseSchema):
    """Request for bulk delete operations."""

    ids: List[UUID] = Field(..., min_length=1, max_length=100)


class BulkUpdateRequest(BaseSchema, Generic[T]):
    """Request for bulk update operations."""

    ids: List[UUID] = Field(..., min_length=1, max_length=100)
    data: T


class StatusUpdateRequest(BaseSchema):
    """Request for status update."""

    status: str
    reason: Optional[str] = None
