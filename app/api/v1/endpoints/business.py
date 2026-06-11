import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_manager_or_above, get_current_owner, get_current_user, get_db
from app.models.user import User
from app.schemas.business import BusinessResponse, BusinessUpdate, EmployeeResponse, EmployeeUpdate
from app.services.business_service import business_service

router = APIRouter()


@router.get("/", response_model=BusinessResponse)
async def get_business(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await business_service.get_business(db, current_user.business_id)


@router.patch("/", response_model=BusinessResponse)
async def update_business(
    body: BusinessUpdate,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    return await business_service.update_business(
        db,
        current_user.business_id,
        name=body.name,
        currency=body.currency,
        language=body.language,
    )


@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    location_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await business_service.get_employees(
        db, current_user.business_id, location_id
    )


@router.patch("/employees/{user_id}", response_model=EmployeeResponse)
async def update_employee(
    user_id: uuid.UUID,
    body: EmployeeUpdate,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    return await business_service.update_employee(
        db,
        current_user.business_id,
        user_id,
        role=body.role,
        location_id=body.location_id,
        is_active=body.is_active,
    )


@router.delete("/employees/{user_id}", status_code=204)
async def remove_employee(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    await business_service.remove_employee(db, current_user.business_id, user_id)
