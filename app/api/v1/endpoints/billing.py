"""
Billing management endpoints.
"""
from typing import Annotated, Optional
from uuid import UUID
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import Permission, require_permissions
from app.core.exceptions import NotFoundError, ValidationError
from app.api.v1.schemas.billing import (
    BillCreate,
    BillUpdate,
    BillResponse,
    BillListResponse,
    BillDetailResponse,
    BillFilter,
    BillItemCreate,
    PaymentCreate,
    PaymentResponse,
    RefundRequest,
    BillStats,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.billing import BillingService
from app.models.user import User
from app.models.enums import UserRole, BillStatus, PaymentStatus, PaymentMethod

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/bills", response_model=BillListResponse)
@require_permissions(Permission.VIEW_BILL)
async def list_bills(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[UUID] = None,
    admission_id: Optional[UUID] = None,
    status: Optional[BillStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    List bills with filtering and pagination.

    Requires: VIEW_BILL permission
    """
    billing_service = BillingService(db)

    filters = BillFilter(
        patient_id=patient_id,
        admission_id=admission_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    bills = await billing_service.get_bills(
        skip=skip,
        limit=limit,
        filters=filters,
        current_user=current_user,
    )

    total = await billing_service.count_bills(
        filters=filters,
        current_user=current_user,
    )

    return BillListResponse(
        items=[BillResponse.model_validate(b) for b in bills],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/bills/me", response_model=BillListResponse)
async def get_my_bills(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[BillStatus] = None,
    unpaid_only: bool = False,
):
    """
    Get current user's bills.

    Only for patients.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this endpoint",
        )

    billing_service = BillingService(db)

    bills = await billing_service.get_my_bills(
        user=current_user,
        skip=skip,
        limit=limit,
        status=status,
        unpaid_only=unpaid_only,
    )

    total = await billing_service.count_my_bills(
        user=current_user,
        status=status,
        unpaid_only=unpaid_only,
    )

    return BillListResponse(
        items=[BillResponse.model_validate(b) for b in bills],
        total=total,
        page=skip // limit + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.get("/bills/pending")
@require_permissions(Permission.VIEW_BILL)
async def get_pending_bills(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get pending (unpaid/partial) bills.

    Requires: VIEW_BILL permission
    """
    billing_service = BillingService(db)

    bills = await billing_service.get_pending_bills(
        branch_id=branch_id,
        skip=skip,
        limit=limit,
    )

    return {"items": [BillResponse.model_validate(b) for b in bills]}


@router.get("/stats", response_model=BillStats)
@require_permissions(Permission.VIEW_BILLING_REPORT)
async def get_billing_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    Get billing statistics.

    Requires: VIEW_BILLING_REPORT permission
    """
    billing_service = BillingService(db)
    stats = await billing_service.get_billing_stats(
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )
    return stats


@router.get("/bills/{bill_id}", response_model=BillDetailResponse)
@require_permissions(Permission.VIEW_BILL)
async def get_bill(
    bill_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific bill by ID.

    Requires: VIEW_BILL permission
    """
    billing_service = BillingService(db)

    try:
        bill = await billing_service.get_bill(
            bill_id=bill_id,
            current_user=current_user,
        )
        return BillDetailResponse.model_validate(bill)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )


@router.post("/bills", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.CREATE_BILL)
async def create_bill(
    bill_data: BillCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new bill.

    Requires: CREATE_BILL permission
    """
    billing_service = BillingService(db)

    try:
        bill = await billing_service.create_bill(
            created_by=current_user.id,
            **bill_data.model_dump(),
        )
        return BillResponse.model_validate(bill)
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


@router.put("/bills/{bill_id}", response_model=BillResponse)
@require_permissions(Permission.UPDATE_BILL)
async def update_bill(
    bill_id: UUID,
    bill_data: BillUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a bill.

    Requires: UPDATE_BILL permission
    """
    billing_service = BillingService(db)

    try:
        bill = await billing_service.update_bill(
            bill_id=bill_id,
            **bill_data.model_dump(exclude_unset=True),
        )
        return BillResponse.model_validate(bill)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/bills/{bill_id}/items", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_BILL)
async def add_bill_item(
    bill_id: UUID,
    item_data: BillItemCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add an item to a bill.

    Requires: UPDATE_BILL permission
    """
    billing_service = BillingService(db)

    try:
        await billing_service.add_item(
            bill_id=bill_id,
            **item_data.model_dump(),
        )
        return SuccessResponse(message="Item added to bill")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/bills/{bill_id}/items/{item_id}", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_BILL)
async def remove_bill_item(
    bill_id: UUID,
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove an item from a bill.

    Requires: UPDATE_BILL permission
    """
    billing_service = BillingService(db)

    try:
        await billing_service.remove_item(bill_id, item_id)
        return SuccessResponse(message="Item removed from bill")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill or item not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/bills/{bill_id}/finalize", response_model=SuccessResponse)
@require_permissions(Permission.UPDATE_BILL)
async def finalize_bill(
    bill_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Finalize a bill (lock from further edits).

    Requires: UPDATE_BILL permission
    """
    billing_service = BillingService(db)

    try:
        await billing_service.finalize_bill(bill_id)
        return SuccessResponse(message="Bill finalized successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Payment endpoints
@router.get("/bills/{bill_id}/payments", response_model=list[PaymentResponse])
@require_permissions(Permission.VIEW_BILL)
async def get_bill_payments(
    bill_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get all payments for a bill.

    Requires: VIEW_BILL permission
    """
    billing_service = BillingService(db)

    try:
        payments = await billing_service.get_bill_payments(bill_id)
        return [PaymentResponse.model_validate(p) for p in payments]
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )


@router.post("/bills/{bill_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(Permission.PROCESS_PAYMENT)
async def record_payment(
    bill_id: UUID,
    payment_data: PaymentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Record a payment for a bill.

    Requires: PROCESS_PAYMENT permission
    """
    billing_service = BillingService(db)

    try:
        payment = await billing_service.record_payment(
            bill_id=bill_id,
            processed_by=current_user.id,
            **payment_data.model_dump(),
        )
        return PaymentResponse.model_validate(payment)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/payments/{payment_id}/refund", response_model=SuccessResponse)
@require_permissions(Permission.PROCESS_REFUND)
async def process_refund(
    payment_id: UUID,
    refund_data: RefundRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Process a refund for a payment.

    Requires: PROCESS_REFUND permission
    """
    billing_service = BillingService(db)

    try:
        await billing_service.process_refund(
            payment_id=payment_id,
            amount=refund_data.amount,
            reason=refund_data.reason,
            processed_by=current_user.id,
        )
        return SuccessResponse(message="Refund processed successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/bills/{bill_id}", response_model=SuccessResponse)
@require_permissions(Permission.DELETE_BILL)
async def delete_bill(
    bill_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a bill.

    Requires: DELETE_BILL permission
    """
    billing_service = BillingService(db)

    try:
        await billing_service.delete_bill(bill_id)
        return SuccessResponse(message="Bill deleted successfully")
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
