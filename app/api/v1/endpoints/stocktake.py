import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_manager_or_above, get_current_user, get_db
from app.models.user import User
from app.schemas.stocktake import (
    StocktakeItemResponse,
    StocktakeListResponse,
    StocktakeResponse,
    UpdateStocktakeItemRequest,
)
from app.services.stocktake_service import stocktake_service

router = APIRouter()


class StartStocktakeRequest(BaseModel):
    location_id: uuid.UUID


@router.get("/", response_model=StocktakeListResponse)
async def list_stocktakes(
    location_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stocktake_service.get_stocktakes(
        db,
        current_user.business_id,
        location_id=location_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{stocktake_id}", response_model=StocktakeResponse)
async def get_stocktake(
    stocktake_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stocktake_service.get_stocktake_by_id(
        db, current_user.business_id, stocktake_id
    )


@router.post("/", response_model=StocktakeResponse, status_code=201)
async def create_stocktake(
    body: StartStocktakeRequest,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await stocktake_service.create_stocktake(
        db, current_user.business_id, body.location_id, current_user.id
    )


@router.patch("/{stocktake_id}/items/{item_id}", response_model=StocktakeItemResponse)
async def update_stocktake_item(
    stocktake_id: uuid.UUID,
    item_id: uuid.UUID,
    body: UpdateStocktakeItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stocktake_service.update_stocktake_item(
        db, current_user.business_id, stocktake_id, item_id, body.actual_quantity
    )


@router.post("/{stocktake_id}/complete", response_model=StocktakeResponse)
async def complete_stocktake(
    stocktake_id: uuid.UUID,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await stocktake_service.complete_stocktake(
        db, current_user.business_id, stocktake_id
    )
