import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_owner, get_current_user, get_db
from app.models.user import User
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate
from app.services.location_service import location_service

router = APIRouter()


@router.get("/", response_model=list[LocationResponse])
async def list_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await location_service.get_locations(db, current_user.business_id)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await location_service.get_location_by_id(
        db, current_user.business_id, location_id
    )


@router.post("/", response_model=LocationResponse, status_code=201)
async def create_location(
    body: LocationCreate,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    return await location_service.create_location(
        db,
        current_user.business_id,
        name=body.name,
        address=body.address,
        currency=body.currency,
    )


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdate,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    return await location_service.update_location(
        db,
        current_user.business_id,
        location_id,
        name=body.name,
        address=body.address,
        currency=body.currency,
        is_active=body.is_active,
    )


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    await location_service.delete_location(db, current_user.business_id, location_id)
