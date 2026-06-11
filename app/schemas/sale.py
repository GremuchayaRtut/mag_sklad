import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.enums import SaleStatus


class SaleItemInput(BaseModel):
    product_id: uuid.UUID
    quantity: Annotated[Decimal, Field(gt=0, description="Must be > 0")]


class SaleCreate(BaseModel):
    location_id: uuid.UUID
    items: Annotated[list[SaleItemInput], Field(min_length=1)]
    note: str | None = None


class SaleItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: Decimal
    sale_price: Decimal
    purchase_price: Decimal


class SaleResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    status: SaleStatus
    total_amount: Decimal
    total_cost: Decimal
    note: str | None
    created_at: datetime
    items: list[SaleItemResponse] = []

    model_config = {"from_attributes": True}


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    total: int
    skip: int
    limit: int


class SalesSummary(BaseModel):
    total_revenue: Decimal
    total_cost: Decimal
    total_profit: Decimal
    profit_margin: Decimal
    sales_count: int
    average_sale: Decimal
    date_from: date | None = None
    date_to: date | None = None
