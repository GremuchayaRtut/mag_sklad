import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_manager_or_above, get_current_user, get_db
from app.models.user import User
from app.schemas.sale import SaleCreate, SaleListResponse, SaleResponse, SalesSummary
from app.services.sale_service import sale_service

router = APIRouter()


@router.get("/summary", response_model=SalesSummary)
async def sales_summary(
    location_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.get_sales_summary(
        db,
        current_user.business_id,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/", response_model=SaleListResponse)
async def list_sales(
    location_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.get_sales(
        db,
        current_user.business_id,
        location_id=location_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.get_sale_by_id(db, current_user.business_id, sale_id)


@router.post("/", response_model=SaleResponse, status_code=201)
async def create_sale(
    body: SaleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.create_sale(
        db,
        current_user.business_id,
        body.location_id,
        current_user.id,
        body,
    )


@router.post("/{sale_id}/cancel", response_model=SaleResponse)
async def cancel_sale(
    sale_id: uuid.UUID,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await sale_service.cancel_sale(db, current_user.business_id, sale_id)
