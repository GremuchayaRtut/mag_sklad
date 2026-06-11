import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_manager_or_above, get_current_owner, get_db
from app.models.user import User
from app.schemas.report import DashboardStats, LocationReportItem, SalesReport, TopProductItem
from app.services.report_service import report_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    location_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_dashboard(db, current_user.business_id, location_id)


@router.get("/sales", response_model=SalesReport)
async def sales_report(
    period: str = Query(default="week", pattern="^(day|week|month|quarter|year)$"),
    location_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_sales_report(
        db, current_user.business_id, period, location_id
    )


@router.get("/top-products", response_model=list[TopProductItem])
async def top_products(
    location_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_top_products(
        db,
        current_user.business_id,
        location_id=location_id,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/locations", response_model=list[LocationReportItem])
async def locations_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_locations_report(
        db,
        current_user.business_id,
        date_from=date_from,
        date_to=date_to,
    )
