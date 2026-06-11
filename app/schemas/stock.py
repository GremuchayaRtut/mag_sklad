import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class StockRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity: Decimal
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockAdjust(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity: Decimal
