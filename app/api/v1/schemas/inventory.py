"""Inventory schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.db.models.enums import InventoryTransactionType
from .base import BaseSchema, IDTimestampSchema


# ==========================================
# MEDICINE
# ==========================================


class MedicineBase(BaseSchema):
    """Base medicine schema."""

    name: str = Field(..., max_length=255)
    generic_name: Optional[str] = Field(None, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    manufacturer: Optional[str] = Field(None, max_length=255)
    category: str = Field(..., max_length=100)
    dosage_form: str = Field(..., max_length=100)
    strength: Optional[str] = Field(None, max_length=100)
    unit: str = Field(..., max_length=50)
    description: Optional[str] = None
    side_effects: Optional[str] = None
    contraindications: Optional[str] = None
    storage_conditions: Optional[str] = Field(None, max_length=255)
    requires_prescription: bool = True


class MedicineCreate(MedicineBase):
    """Create medicine schema."""

    pass


class MedicineUpdate(BaseSchema):
    """Update medicine schema."""

    name: Optional[str] = Field(None, max_length=255)
    generic_name: Optional[str] = Field(None, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    manufacturer: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    dosage_form: Optional[str] = Field(None, max_length=100)
    strength: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    side_effects: Optional[str] = None
    contraindications: Optional[str] = None
    storage_conditions: Optional[str] = Field(None, max_length=255)
    requires_prescription: Optional[bool] = None
    is_active: Optional[bool] = None


class MedicineResponse(IDTimestampSchema, MedicineBase):
    """Medicine response schema."""

    medicine_code: str  # Auto-generated MED-001
    is_active: bool


class MedicineListResponse(BaseSchema):
    """Medicine list item."""

    id: UUID
    medicine_code: str
    name: str
    generic_name: Optional[str] = None
    category: str
    dosage_form: str
    strength: Optional[str] = None
    requires_prescription: bool
    is_active: bool


class MedicineDetailResponse(MedicineResponse):
    """Detailed medicine response."""

    total_stock: int = 0
    branches_stocked: int = 0


# ==========================================
# INVENTORY
# ==========================================


class InventoryBase(BaseSchema):
    """Base inventory schema."""

    quantity: int = Field(0, ge=0)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    selling_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None
    reorder_level: int = Field(10, ge=0)
    max_stock_level: int = Field(1000, ge=0)
    location: Optional[str] = Field(None, max_length=100)


class InventoryCreate(InventoryBase):
    """Create inventory schema."""

    medicine_id: UUID
    branch_id: UUID
    supplier: Optional[str] = Field(None, max_length=255)


class InventoryUpdate(BaseSchema):
    """Update inventory schema."""

    quantity: Optional[int] = Field(None, ge=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None
    reorder_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    supplier: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class InventoryResponse(IDTimestampSchema, InventoryBase):
    """Inventory response schema."""

    medicine_id: UUID
    branch_id: UUID
    supplier: Optional[str] = None
    is_active: bool
    last_restocked: Optional[datetime] = None
    # Joined fields
    medicine_name: Optional[str] = None
    medicine_code: Optional[str] = None
    branch_name: Optional[str] = None

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below reorder level."""
        return self.quantity <= self.reorder_level

    @property
    def is_expired(self) -> bool:
        """Check if medicine is expired."""
        if self.expiry_date:
            return self.expiry_date < date.today()
        return False

    @property
    def is_expiring_soon(self) -> bool:
        """Check if medicine is expiring within 30 days."""
        if self.expiry_date:
            from datetime import timedelta
            return self.expiry_date <= date.today() + timedelta(days=30)
        return False


class InventoryListResponse(BaseSchema):
    """Inventory list item."""

    id: UUID
    medicine_id: UUID
    medicine_name: str
    medicine_code: str
    branch_id: UUID
    branch_name: str
    quantity: int
    unit_price: Decimal
    selling_price: Decimal
    expiry_date: Optional[date] = None
    reorder_level: int
    is_low_stock: bool
    is_active: bool


# ==========================================
# STOCK ADJUSTMENT
# ==========================================


class StockAdjustmentRequest(BaseSchema):
    """Stock adjustment request."""

    inventory_id: UUID
    quantity: int = Field(..., description="Positive for add, negative for subtract")
    transaction_type: InventoryTransactionType
    reason: str = Field(..., min_length=1, max_length=500)
    reference_number: Optional[str] = Field(None, max_length=100)
    batch_number: Optional[str] = Field(None, max_length=100)


class StockAdjustmentResponse(BaseSchema):
    """Stock adjustment response."""

    inventory_id: UUID
    previous_quantity: int
    adjusted_quantity: int
    new_quantity: int
    transaction_type: InventoryTransactionType
    adjusted_at: datetime
    adjusted_by: Optional[UUID] = None


# ==========================================
# DISPENSE LOG
# ==========================================


class DispenseLogBase(BaseSchema):
    """Base dispense log schema."""

    quantity: int = Field(..., ge=1)
    notes: Optional[str] = None


class DispenseLogCreate(DispenseLogBase):
    """Create dispense log schema."""

    inventory_id: UUID
    prescription_id: Optional[UUID] = None
    prescription_item_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None


class DispenseLogResponse(IDTimestampSchema, DispenseLogBase):
    """Dispense log response schema."""

    inventory_id: UUID
    prescription_id: Optional[UUID] = None
    prescription_item_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    dispensed_by: Optional[UUID] = None
    unit_price: Decimal
    total_price: Decimal
    batch_number: Optional[str] = None
    # Joined fields
    medicine_name: Optional[str] = None
    patient_name: Optional[str] = None
    dispensed_by_name: Optional[str] = None


# ==========================================
# INVENTORY FILTERS
# ==========================================


class InventoryFilterParams(BaseSchema):
    """Inventory filter parameters."""

    medicine_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    search: Optional[str] = Field(None, description="Search in medicine name")
    category: Optional[str] = None
    is_low_stock: Optional[bool] = None
    is_expired: Optional[bool] = None
    is_expiring_soon: Optional[bool] = None
    is_active: Optional[bool] = None


class MedicineFilterParams(BaseSchema):
    """Medicine filter parameters."""

    search: Optional[str] = Field(None, description="Search in name or generic name")
    category: Optional[str] = None
    dosage_form: Optional[str] = None
    requires_prescription: Optional[bool] = None
    is_active: Optional[bool] = None


# ==========================================
# INVENTORY STATISTICS
# ==========================================


class InventoryStatsResponse(BaseSchema):
    """Inventory statistics response."""

    total_medicines: int
    total_stock_value: Decimal
    low_stock_items: int
    out_of_stock_items: int
    expired_items: int
    expiring_soon_items: int
    by_category: dict[str, int]
    by_branch: dict[str, int]


class StockAlertResponse(BaseSchema):
    """Stock alert response."""

    low_stock: list[InventoryListResponse]
    expired: list[InventoryListResponse]
    expiring_soon: list[InventoryListResponse]
