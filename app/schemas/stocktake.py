import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.enums import StocktakeStatus


class UpdateStocktakeItemRequest(BaseModel):
    actual_quantity: Annotated[float, Field(ge=0)]


class StocktakeItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    expected_quantity: float
    actual_quantity: float | None
    is_checked: bool


class StocktakeResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    status: StocktakeStatus
    created_at: datetime
    completed_at: datetime | None
    items: list[StocktakeItemResponse] = []

    model_config = {"from_attributes": True}


class StocktakeListResponse(BaseModel):
    items: list[StocktakeResponse]
    total: int
