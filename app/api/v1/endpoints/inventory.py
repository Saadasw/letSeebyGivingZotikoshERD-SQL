"""
Inventory management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.inventory import (
    MedicineCreate,
    MedicineUpdate,
    MedicineResponse,
    MedicineListResponse,
    MedicineDetailResponse,
    MedicineFilter,
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    InventoryListResponse,
    StockAdjustmentRequest,
    InventoryStats,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.inventory import InventoryService
from app.models.user import User

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# Medicine endpoints
@router.get("/medicines", response_model=MedicineListResponse)
@require_permissions(Permission.VIEW_INVENTORY)
async def list_medicines(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    manufacturer: Optional[str] = None,
    is_active: Optional[bool] = True,
):
    """
    List all medicines with filtering and pagination.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    filters = MedicineFilter(
        search=search,
        category=category,
        manufacturer=manufacturer,
        is_active=is_active,
    )

    medicines = await inventory_service.get_medicines(
        skip=skip,
        limit=limit,
        filters=filters,
    )

    total = await inventory_service.count_medicines(filters=filters)

    return MedicineListResponse(
        items=[MedicineResponse.model_validate(m) for m in medicines],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/medicines/{medicine_id}", response_model=MedicineDetailResponse)
@require_permissions(Permission.VIEW_INVENTORY)
async def get_medicine(
    medicine_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific medicine by ID.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    try:
        medicine = await inventory_service.get_medicine(medicine_id)
        return MedicineDetailResponse.model_validate(medicine)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )


@router.post("/medicines", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_MEDICINE)
async def create_medicine(
    medicine_data: MedicineCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new medicine.

    Requires: CREATE_MEDICINE permission
    """
    inventory_service = InventoryService(db)

    try:
        medicine = await inventory_service.create_medicine(
            created_by=current_user.id,
            **medicine_data.model_dump(),
        )
        return MedicineResponse.model_validate(medicine)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/medicines/{medicine_id}", response_model=MedicineResponse)
@require_permissions(Permission.UPDATE_MEDICINE)
async def update_medicine(
    medicine_id: UUID,
    medicine_data: MedicineUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a medicine.

    Requires: UPDATE_MEDICINE permission
    """
    inventory_service = InventoryService(db)

    try:
        medicine = await inventory_service.update_medicine(
            medicine_id=medicine_id,
            **medicine_data.model_dump(exclude_unset=True),
        )
        return MedicineResponse.model_validate(medicine)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/medicines/{medicine_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_MEDICINE)
async def delete_medicine(
    medicine_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a medicine.

    Requires: DELETE_MEDICINE permission
    """
    inventory_service = InventoryService(db)

    try:
        await inventory_service.delete_medicine(medicine_id)
        return SuccessResponse(message="Medicine deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )


# Inventory/Stock endpoints
@router.get("", response_model=InventoryListResponse)
@require_permissions(Permission.VIEW_INVENTORY)
async def list_inventory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    medicine_id: Optional[UUID] = None,
    low_stock_only: bool = False,
    expiring_soon: bool = False,
):
    """
    List inventory items with filtering and pagination.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    items = await inventory_service.get_inventory(
        skip=skip,
        limit=limit,
        branch_id=branch_id,
        medicine_id=medicine_id,
        low_stock_only=low_stock_only,
        expiring_soon=expiring_soon,
    )

    total = await inventory_service.count_inventory(
        branch_id=branch_id,
        medicine_id=medicine_id,
        low_stock_only=low_stock_only,
        expiring_soon=expiring_soon,
    )

    return InventoryListResponse(
        items=[InventoryResponse.model_validate(i) for i in items],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/stats", response_model=InventoryStats)
@require_permissions(Permission.VIEW_INVENTORY)
async def get_inventory_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
):
    """
    Get inventory statistics.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)
    stats = await inventory_service.get_inventory_stats(branch_id)
    return stats


@router.get("/low-stock")
@require_permissions(Permission.VIEW_INVENTORY)
async def get_low_stock_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
):
    """
    Get items with low stock.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    items = await inventory_service.get_low_stock(branch_id)

    return {"items": [InventoryResponse.model_validate(i) for i in items]}


@router.get("/expiring")
@require_permissions(Permission.VIEW_INVENTORY)
async def get_expiring_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
    branch_id: Optional[UUID] = None,
):
    """
    Get items expiring within specified days.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    items = await inventory_service.get_expiring(
        days=days,
        branch_id=branch_id,
    )

    return {"items": [InventoryResponse.model_validate(i) for i in items]}


@router.get("/{inventory_id}", response_model=InventoryResponse)
@require_permissions(Permission.VIEW_INVENTORY)
async def get_inventory_item(
    inventory_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific inventory item.

    Requires: VIEW_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    try:
        item = await inventory_service.get_inventory_item(inventory_id)
        return InventoryResponse.model_validate(item)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.MANAGE_INVENTORY)
async def add_inventory(
    inventory_data: InventoryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add inventory (stock) for a medicine at a branch.

    Requires: MANAGE_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    try:
        item = await inventory_service.add_inventory(
            created_by=current_user.id,
            **inventory_data.model_dump(),
        )
        return InventoryResponse.model_validate(item)
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


@router.put("/{inventory_id}", response_model=InventoryResponse)
@require_permissions(Permission.MANAGE_INVENTORY)
async def update_inventory(
    inventory_id: UUID,
    inventory_data: InventoryUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update inventory item.

    Requires: MANAGE_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    try:
        item = await inventory_service.update_inventory(
            inventory_id=inventory_id,
            **inventory_data.model_dump(exclude_unset=True),
        )
        return InventoryResponse.model_validate(item)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{inventory_id}/adjust", response_model=SuccessResponse)
@require_permissions(Permission.MANAGE_INVENTORY)
async def adjust_stock(
    inventory_id: UUID,
    adjustment: StockAdjustmentRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Adjust stock quantity (add or subtract).

    Requires: MANAGE_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    try:
        await inventory_service.adjust_stock(
            inventory_id=inventory_id,
            quantity=adjustment.quantity,
            adjustment_type=adjustment.adjustment_type,
            reason=adjustment.reason,
            adjusted_by=current_user.id,
        )
        return SuccessResponse(message="Stock adjusted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{inventory_id}", response_model=SuccessResponse)
@require_permissions(Permission.MANAGE_INVENTORY)
async def delete_inventory(
    inventory_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an inventory item.

    Requires: MANAGE_INVENTORY permission
    """
    inventory_service = InventoryService(db)

    try:
        await inventory_service.delete_inventory(inventory_id)
        return SuccessResponse(message="Inventory item deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )
