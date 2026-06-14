import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.location import Location
from app.models.product import Category, Product
from app.models.stock import Stock
from app.schemas.product import (
    CategoryResponse,
    ExcelImportResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    ProductWithStock,
    StockByLocation,
)
from app.utils.barcode_gen import generate_internal_barcode
from app.utils.excel_import import parse_products_excel
from app.utils.r2 import delete_product_photo, upload_product_photo


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_decimal(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _product_response(
    product: Product,
    category_name: str | None = None,
) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        barcode=product.barcode,
        internal_barcode=product.internal_barcode,
        sku=product.sku,
        unit=product.unit,
        photo_url=product.photo_url,
        sale_price=_to_decimal(product.sale_price),
        purchase_price=_to_decimal(product.purchase_price),
        min_stock=product.min_stock,
        is_active=product.is_active,
        category_id=product.category_id,
        category_name=category_name,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def _load_stocks(
    db: AsyncSession,
    product_ids: list[uuid.UUID],
    location_id: uuid.UUID | None = None,
) -> dict[uuid.UUID, list[StockByLocation]]:
    if not product_ids:
        return {}

    stmt = (
        select(Stock, Location.name.label("location_name"))
        .join(Location, Stock.location_id == Location.id)
        .where(Stock.product_id.in_(product_ids))
    )
    if location_id:
        stmt = stmt.where(Stock.location_id == location_id)

    result = await db.execute(stmt)
    stocks_map: dict[uuid.UUID, list[StockByLocation]] = defaultdict(list)
    for stock, loc_name in result.all():
        stocks_map[stock.product_id].append(
            StockByLocation(
                location_id=stock.location_id,
                location_name=loc_name,
                quantity=_to_decimal(stock.quantity),
            )
        )
    return stocks_map


def _with_stock(
    product: Product,
    category_name: str | None,
    stocks: list[StockByLocation],
) -> ProductWithStock:
    total = float(sum(s.quantity for s in stocks))
    return ProductWithStock(
        id=product.id,
        name=product.name,
        description=product.description,
        barcode=product.barcode,
        internal_barcode=product.internal_barcode,
        sku=product.sku,
        unit=product.unit,
        photo_url=product.photo_url,
        sale_price=_to_decimal(product.sale_price),
        purchase_price=_to_decimal(product.purchase_price),
        min_stock=product.min_stock,
        is_active=product.is_active,
        category_id=product.category_id,
        category_name=category_name,
        created_at=product.created_at,
        updated_at=product.updated_at,
        stocks=stocks,
        total_stock=total,
    )


# ── Service class ─────────────────────────────────────────────────────────────


class ProductService:

    # ── Categories ────────────────────────────────────────────────────────────

    async def get_categories(
        self, db: AsyncSession, business_id: uuid.UUID
    ) -> list[CategoryResponse]:
        result = await db.execute(
            select(Category)
            .where(Category.business_id == business_id)
            .order_by(Category.name)
        )
        return [CategoryResponse.model_validate(c) for c in result.scalars()]

    async def create_category(
        self, db: AsyncSession, business_id: uuid.UUID, name: str
    ) -> CategoryResponse:
        duplicate = await db.scalar(
            select(Category).where(
                Category.business_id == business_id, Category.name == name
            )
        )
        if duplicate:
            raise BadRequestError(f"Category '{name}' already exists")

        category = Category(
            business_id=business_id,
            name=name,
            created_at=datetime.now(timezone.utc),
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return CategoryResponse.model_validate(category)

    async def delete_category(
        self, db: AsyncSession, business_id: uuid.UUID, category_id: uuid.UUID
    ) -> None:
        category = await db.scalar(
            select(Category).where(
                Category.id == category_id, Category.business_id == business_id
            )
        )
        if category is None:
            raise NotFoundError("Category not found")

        # Detach products instead of cascading delete
        products = await db.execute(
            select(Product).where(Product.category_id == category_id)
        )
        for product in products.scalars():
            product.category_id = None

        await db.delete(category)
        await db.commit()

    # ── Products — list / search ──────────────────────────────────────────────

    async def get_products(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        *,
        location_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        search: str | None = None,
        low_stock_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> ProductListResponse:
        conditions = [
            Product.business_id == business_id,
            Product.is_active.is_(True),
        ]
        if category_id:
            conditions.append(Product.category_id == category_id)
        if search:
            conditions.append(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.barcode == search,
                    Product.internal_barcode == search,
                )
            )

        # Low-stock filter via a subquery so it doesn't collide with other joins
        low_stock_sq = None
        if low_stock_only:
            if location_id:
                low_stock_sq = (
                    select(Stock.product_id, Stock.quantity.label("qty"))
                    .where(Stock.location_id == location_id)
                    .subquery()
                )
            else:
                low_stock_sq = (
                    select(
                        Stock.product_id,
                        func.sum(Stock.quantity).label("qty"),
                    )
                    .group_by(Stock.product_id)
                    .subquery()
                )

        def _apply_low_stock(stmt):
            if low_stock_sq is not None:
                stmt = stmt.outerjoin(
                    low_stock_sq, low_stock_sq.c.product_id == Product.id
                ).where(
                    func.coalesce(low_stock_sq.c.qty, 0) <= Product.min_stock
                )
            return stmt

        # Count
        count_stmt = _apply_low_stock(
            select(func.count(Product.id))
            .select_from(Product)
            .where(and_(*conditions))
        )
        total: int = (await db.scalar(count_stmt)) or 0

        # Data — include category name via LEFT JOIN
        data_stmt = _apply_low_stock(
            select(Product, Category.name.label("category_name"))
            .outerjoin(Category, Product.category_id == Category.id)
            .where(and_(*conditions))
            .order_by(Product.name)
            .offset(skip)
            .limit(limit)
        )
        rows = (await db.execute(data_stmt)).all()

        # Stocks for fetched products
        product_ids = [row[0].id for row in rows]
        stocks_map = await _load_stocks(db, product_ids, location_id)

        items = [
            _with_stock(product, cat_name, stocks_map.get(product.id, []))
            for product, cat_name in rows
        ]
        return ProductListResponse(items=items, total=total, skip=skip, limit=limit)

    # ── Products — single fetch ───────────────────────────────────────────────

    async def get_product_by_id(
        self, db: AsyncSession, business_id: uuid.UUID, product_id: uuid.UUID
    ) -> ProductWithStock:
        product = await db.scalar(
            select(Product).where(
                Product.id == product_id, Product.business_id == business_id
            )
        )
        if product is None:
            raise NotFoundError("Product not found")

        cat_name: str | None = None
        if product.category_id:
            cat_name = await db.scalar(
                select(Category.name).where(Category.id == product.category_id)
            )

        stocks_map = await _load_stocks(db, [product.id])
        return _with_stock(product, cat_name, stocks_map.get(product.id, []))

    async def get_product_by_barcode(
        self, db: AsyncSession, business_id: uuid.UUID, barcode: str
    ) -> ProductWithStock:
        product = await db.scalar(
            select(Product).where(
                Product.business_id == business_id,
                or_(
                    Product.barcode == barcode,
                    Product.internal_barcode == barcode,
                ),
            )
        )
        if product is None:
            raise NotFoundError("Product not found")

        cat_name: str | None = None
        if product.category_id:
            cat_name = await db.scalar(
                select(Category.name).where(Category.id == product.category_id)
            )

        stocks_map = await _load_stocks(db, [product.id])
        return _with_stock(product, cat_name, stocks_map.get(product.id, []))

    # ── Products — mutations ──────────────────────────────────────────────────

    async def create_product(
        self, db: AsyncSession, business_id: uuid.UUID, data: ProductCreate
    ) -> ProductResponse:
        if data.barcode:
            dup = await db.scalar(
                select(Product).where(
                    Product.business_id == business_id,
                    Product.barcode == data.barcode,
                )
            )
            if dup:
                raise BadRequestError(
                    f"Product with barcode '{data.barcode}' already exists"
                )

        internal_bc = generate_internal_barcode(business_id)

        product = Product(
            business_id=business_id,
            name=data.name,
            description=data.description,
            barcode=data.barcode,
            internal_barcode=internal_bc,
            sku=data.sku,
            unit=data.unit,
            sale_price=data.sale_price,
            purchase_price=data.purchase_price,
            min_stock=data.min_stock,
            category_id=data.category_id,
        )
        db.add(product)
        await db.flush()

        # Create stock=0 for every active location in this business
        loc_ids = (
            await db.execute(
                select(Location.id).where(
                    Location.business_id == business_id,
                    Location.is_active.is_(True),
                )
            )
        ).scalars().all()

        for loc_id in loc_ids:
            db.add(Stock(product_id=product.id, location_id=loc_id, quantity=0))

        await db.commit()
        await db.refresh(product)

        cat_name: str | None = None
        if product.category_id:
            cat_name = await db.scalar(
                select(Category.name).where(Category.id == product.category_id)
            )
        return _product_response(product, cat_name)

    async def update_product(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        product_id: uuid.UUID,
        data: ProductUpdate,
    ) -> ProductResponse:
        product = await db.scalar(
            select(Product).where(
                Product.id == product_id, Product.business_id == business_id
            )
        )
        if product is None:
            raise NotFoundError("Product not found")

        if data.barcode is not None and data.barcode != product.barcode:
            dup = await db.scalar(
                select(Product).where(
                    Product.business_id == business_id,
                    Product.barcode == data.barcode,
                    Product.id != product_id,
                )
            )
            if dup:
                raise BadRequestError(
                    f"Product with barcode '{data.barcode}' already exists"
                )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)

        cat_name: str | None = None
        if product.category_id:
            cat_name = await db.scalar(
                select(Category.name).where(Category.id == product.category_id)
            )
        return _product_response(product, cat_name)

    async def delete_product(
        self, db: AsyncSession, business_id: uuid.UUID, product_id: uuid.UUID
    ) -> None:
        product = await db.scalar(
            select(Product).where(
                Product.id == product_id, Product.business_id == business_id
            )
        )
        if product is None:
            raise NotFoundError("Product not found")
        product.is_active = False
        await db.commit()

    # ── Photo upload ──────────────────────────────────────────────────────────

    async def upload_photo(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        product_id: uuid.UUID,
        file: UploadFile,
    ) -> ProductResponse:
        product = await db.scalar(
            select(Product).where(
                Product.id == product_id, Product.business_id == business_id
            )
        )
        if product is None:
            raise NotFoundError("Product not found")

        if product.photo_url:
            await delete_product_photo(product.photo_url)

        product.photo_url = await upload_product_photo(file, business_id)
        await db.commit()
        await db.refresh(product)

        cat_name: str | None = None
        if product.category_id:
            cat_name = await db.scalar(
                select(Category.name).where(Category.id == product.category_id)
            )
        return _product_response(product, cat_name)

    # ── Excel import ──────────────────────────────────────────────────────────

    async def import_from_excel(
        self, db: AsyncSession, business_id: uuid.UUID, file_bytes: bytes
    ) -> ExcelImportResponse:
        rows = parse_products_excel(file_bytes)  # raises BadRequestError on bad file

        # Load active location IDs once — reused per-product inside the loop
        loc_ids: list[uuid.UUID] = (
            await db.execute(
                select(Location.id).where(
                    Location.business_id == business_id,
                    Location.is_active.is_(True),
                )
            )
        ).scalars().all()

        created = 0
        skipped = 0
        errors: list[str] = []

        for row_num, row in enumerate(rows, start=2):
            # Duplicate barcode check is a read and can sit outside the savepoint
            if row.get("barcode"):
                existing = await db.scalar(
                    select(Product).where(
                        Product.business_id == business_id,
                        Product.barcode == row["barcode"],
                    )
                )
                if existing:
                    skipped += 1
                    continue

            try:
                async with db.begin_nested():
                    # Find or create category
                    category_id: uuid.UUID | None = None
                    if row.get("category"):
                        cat = await db.scalar(
                            select(Category).where(
                                Category.business_id == business_id,
                                Category.name == row["category"],
                            )
                        )
                        if cat is None:
                            cat = Category(
                                business_id=business_id,
                                name=row["category"],
                                created_at=datetime.now(timezone.utc),
                            )
                            db.add(cat)
                            await db.flush()
                        category_id = cat.id

                    internal_bc = generate_internal_barcode(business_id)
                    product = Product(
                        business_id=business_id,
                        name=row["name"],
                        barcode=row.get("barcode"),
                        internal_barcode=internal_bc,
                        unit=row["unit"],
                        category_id=category_id,
                        sale_price=row["sale_price"],
                        purchase_price=row["purchase_price"],
                        min_stock=row.get("min_stock", 0),
                    )
                    db.add(product)
                    await db.flush()

                    for loc_id in loc_ids:
                        db.add(
                            Stock(
                                product_id=product.id,
                                location_id=loc_id,
                                quantity=0,
                            )
                        )

                created += 1

            except Exception as exc:
                errors.append(f"Row {row_num}: {exc}")

        await db.commit()
        return ExcelImportResponse(created=created, skipped=skipped, errors=errors)


product_service = ProductService()
