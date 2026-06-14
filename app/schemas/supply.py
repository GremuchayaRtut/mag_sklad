import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.enums import SupplyStatus


class SupplyItemInput(BaseModel):
    product_id: uuid.UUID
    quantity: Annotated[float, Field(gt=0, description="Must be > 0")]
    purchase_price: Annotated[float, Field(ge=0)]


class SupplyCreate(BaseModel):
    location_id: uuid.UUID
    supplier_name: str | None = None
    invoice_number: str | None = None
    supply_date: date
    note: str | None = None
    items: Annotated[list[SupplyItemInput], Field(min_length=1)]


class SupplyItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: float
    purchase_price: float


class SupplyResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    supplier_name: str | None
    invoice_number: str | None
    status: SupplyStatus
    supply_date: date
    note: str | None
    created_at: datetime
    items: list[SupplyItemResponse] = []

    model_config = {"from_attributes": True}


class SupplyListResponse(BaseModel):
    items: list[SupplyResponse]
    total: int
    skip: int
    limit: int
