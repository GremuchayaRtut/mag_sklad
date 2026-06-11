import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.enums import Currency


class LocationCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    address: str | None = None
    currency: Currency | None = None


class LocationUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    address: str | None = None
    currency: Currency | None = None
    is_active: bool | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    currency: Currency | None
    is_active: bool
    business_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# Legacy aliases kept so existing schemas/__init__ imports don't break
LocationRead = LocationResponse
LocationBase = LocationCreate
