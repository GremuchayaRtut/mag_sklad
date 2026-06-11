import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_manager_or_above, get_current_user, get_db
from app.models.enums import SupplyStatus
from app.models.user import User
from app.schemas.supply import SupplyCreate, SupplyListResponse, SupplyResponse
from app.services.supply_service import supply_service

router = APIRouter()


@router.get("/", response_model=SupplyListResponse)
async def list_supplies(
    location_id: uuid.UUID | None = Query(default=None),
    status: SupplyStatus | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await supply_service.get_supplies(
        db,
        current_user.business_id,
        location_id=location_id,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{supply_id}", response_model=SupplyResponse)
async def get_supply(
    supply_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await supply_service.get_supply_by_id(db, current_user.business_id, supply_id)


@router.post("/", response_model=SupplyResponse, status_code=201)
async def create_supply(
    body: SupplyCreate,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await supply_service.create_supply(
        db, current_user.business_id, current_user.id, body
    )


@router.post("/{supply_id}/confirm", response_model=SupplyResponse)
async def confirm_supply(
    supply_id: uuid.UUID,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await supply_service.confirm_supply(db, current_user.business_id, supply_id)


@router.delete("/{supply_id}", status_code=204)
async def delete_supply(
    supply_id: uuid.UUID,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    await supply_service.delete_supply(db, current_user.business_id, supply_id)
