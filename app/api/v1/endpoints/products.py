import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    get_current_manager_or_above,
    get_current_user,
    get_db,
)
from app.models.user import User
from app.schemas.product import (
    CategoryCreate,
    CategoryResponse,
    ExcelImportResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    ProductWithStock,
)
from app.services.product_service import product_service

router = APIRouter()


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_categories(db, current_user.business_id)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.create_category(db, current_user.business_id, body.name)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    await product_service.delete_category(db, current_user.business_id, category_id)


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=ProductListResponse)
async def list_products(
    category_id: uuid.UUID | None = Query(default=None),
    location_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    low_stock_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_products(
        db,
        current_user.business_id,
        location_id=location_id,
        category_id=category_id,
        search=search,
        low_stock_only=low_stock_only,
        skip=skip,
        limit=limit,
    )


@router.get("/barcode/{barcode}", response_model=ProductWithStock)
async def get_by_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_product_by_barcode(
        db, current_user.business_id, barcode
    )


@router.post("/import/excel", response_model=ExcelImportResponse)
async def import_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    return await product_service.import_from_excel(
        db, current_user.business_id, file_bytes
    )


@router.get("/{product_id}", response_model=ProductWithStock)
async def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_product_by_id(
        db, current_user.business_id, product_id
    )


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    body: ProductCreate,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.create_product(db, current_user.business_id, body)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.update_product(
        db, current_user.business_id, product_id, body
    )


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    await product_service.delete_product(db, current_user.business_id, product_id)


@router.post("/{product_id}/photo", response_model=ProductResponse)
async def upload_photo(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.upload_photo(
        db, current_user.business_id, product_id, file
    )
