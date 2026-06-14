import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.enums import Unit


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    business_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# Keep legacy alias used in schemas/__init__
CategoryRead = CategoryResponse


# ── Stock per location ────────────────────────────────────────────────────────

class StockByLocation(BaseModel):
    location_id: uuid.UUID
    location_name: str
    quantity: float


# ── Product ───────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    barcode: str | None = None
    sku: str | None = None
    unit: Unit = Unit.pcs
    category_id: uuid.UUID | None = None
    sale_price: Annotated[float, Field(ge=0)]
    purchase_price: Annotated[float, Field(ge=0)]
    min_stock: Annotated[int, Field(ge=0)] = 0


class ProductUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    barcode: str | None = None
    sku: str | None = None
    unit: Unit | None = None
    category_id: uuid.UUID | None = None
    sale_price: Annotated[float, Field(ge=0)] | None = None
    purchase_price: Annotated[float, Field(ge=0)] | None = None
    min_stock: Annotated[int, Field(ge=0)] | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    barcode: str | None
    internal_barcode: str | None
    sku: str | None
    unit: Unit
    photo_url: str | None
    sale_price: float
    purchase_price: float
    min_stock: int
    is_active: bool
    category_id: uuid.UUID | None
    category_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Legacy alias
ProductRead = ProductResponse


class ProductWithStock(ProductResponse):
    stocks: list[StockByLocation] = []
    total_stock: float = 0.0


# ── List / import responses ───────────────────────────────────────────────────

class ProductListResponse(BaseModel):
    items: list[ProductWithStock]
    total: int
    skip: int
    limit: int


class BarcodeSearchResponse(BaseModel):
    product: ProductResponse
    stocks: list[StockByLocation]


class ExcelImportResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]
