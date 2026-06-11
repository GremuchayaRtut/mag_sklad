import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enums import StocktakeStatus
from app.models.location import Location
from app.models.product import Product
from app.models.stock import Stock
from app.models.stocktake import Stocktake, StocktakeItem
from app.schemas.stocktake import (
    StocktakeItemResponse,
    StocktakeListResponse,
    StocktakeResponse,
)


def _to_d(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


async def _names_map(db: AsyncSession, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not product_ids:
        return {}
    rows = await db.execute(
        select(Product.id, Product.name).where(Product.id.in_(product_ids))
    )
    return {row[0]: row[1] for row in rows}


def _build_item_response(
    item: StocktakeItem, names: dict[uuid.UUID, str]
) -> StocktakeItemResponse:
    return StocktakeItemResponse(
        id=item.id,
        product_id=item.product_id,
        product_name=names.get(item.product_id, ""),
        expected_quantity=_to_d(item.expected_quantity),
        actual_quantity=_to_d(item.actual_quantity) if item.actual_quantity is not None else None,
        is_checked=item.is_checked,
    )


def _build_stocktake_response(
    stocktake: Stocktake, names: dict[uuid.UUID, str]
) -> StocktakeResponse:
    return StocktakeResponse(
        id=stocktake.id,
        location_id=stocktake.location_id,
        status=stocktake.status,
        created_at=stocktake.created_at,
        completed_at=stocktake.completed_at,
        items=[_build_item_response(i, names) for i in stocktake.items],
    )


class StocktakeService:

    async def get_stocktakes(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        *,
        location_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> StocktakeListResponse:
        conditions = [Stocktake.business_id == business_id]
        if location_id:
            conditions.append(Stocktake.location_id == location_id)

        total: int = (
            await db.scalar(select(func.count(Stocktake.id)).where(*conditions))
        ) or 0

        rows = (
            await db.execute(
                select(Stocktake)
                .options(selectinload(Stocktake.items))
                .where(*conditions)
                .order_by(Stocktake.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        all_product_ids = list({item.product_id for s in rows for item in s.items})
        names = await _names_map(db, all_product_ids)

        return StocktakeListResponse(
            items=[_build_stocktake_response(s, names) for s in rows],
            total=total,
        )

    async def create_stocktake(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        location_id: uuid.UUID,
        created_by_id: uuid.UUID,
    ) -> StocktakeResponse:
        location = await db.scalar(
            select(Location).where(
                Location.id == location_id,
                Location.business_id == business_id,
            )
        )
        if location is None:
            raise BadRequestError("Location not found or does not belong to this business")

        in_progress = await db.scalar(
            select(Stocktake).where(
                Stocktake.location_id == location_id,
                Stocktake.status == StocktakeStatus.in_progress,
            )
        )
        if in_progress is not None:
            raise BadRequestError(
                "An in-progress stocktake already exists for this location"
            )

        stocktake = Stocktake(
            business_id=business_id,
            location_id=location_id,
            created_by=created_by_id,
            status=StocktakeStatus.in_progress,
        )
        db.add(stocktake)
        await db.flush()

        # Snapshot current stock for every active product in this business
        products = (
            await db.execute(
                select(Product).where(
                    Product.business_id == business_id,
                    Product.is_active.is_(True),
                )
            )
        ).scalars().all()

        product_ids = [p.id for p in products]

        stocks: dict[uuid.UUID, Decimal] = {}
        if product_ids:
            stock_rows = await db.execute(
                select(Stock.product_id, Stock.quantity).where(
                    Stock.location_id == location_id,
                    Stock.product_id.in_(product_ids),
                )
            )
            stocks = {row[0]: _to_d(row[1]) for row in stock_rows}

        for product in products:
            db.add(
                StocktakeItem(
                    stocktake_id=stocktake.id,
                    product_id=product.id,
                    expected_quantity=stocks.get(product.id, Decimal("0")),
                    actual_quantity=None,
                    is_checked=False,
                )
            )

        await db.commit()

        stocktake = await db.scalar(
            select(Stocktake)
            .options(selectinload(Stocktake.items))
            .where(Stocktake.id == stocktake.id)
        )
        names = await _names_map(db, product_ids)
        return _build_stocktake_response(stocktake, names)

    async def get_stocktake_by_id(
        self, db: AsyncSession, business_id: uuid.UUID, stocktake_id: uuid.UUID
    ) -> StocktakeResponse:
        stocktake = await db.scalar(
            select(Stocktake)
            .options(selectinload(Stocktake.items))
            .where(
                Stocktake.id == stocktake_id,
                Stocktake.business_id == business_id,
            )
        )
        if stocktake is None:
            raise NotFoundError("Stocktake not found")

        names = await _names_map(db, [i.product_id for i in stocktake.items])
        return _build_stocktake_response(stocktake, names)

    async def update_stocktake_item(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        stocktake_id: uuid.UUID,
        item_id: uuid.UUID,
        actual_quantity: Decimal,
    ) -> StocktakeItemResponse:
        stocktake = await db.scalar(
            select(Stocktake).where(
                Stocktake.id == stocktake_id,
                Stocktake.business_id == business_id,
            )
        )
        if stocktake is None:
            raise NotFoundError("Stocktake not found")
        if stocktake.status == StocktakeStatus.completed:
            raise BadRequestError("Cannot update items of a completed stocktake")

        item = await db.scalar(
            select(StocktakeItem).where(
                StocktakeItem.id == item_id,
                StocktakeItem.stocktake_id == stocktake_id,
            )
        )
        if item is None:
            raise NotFoundError("Stocktake item not found")

        item.actual_quantity = actual_quantity
        item.is_checked = True
        await db.commit()
        await db.refresh(item)

        names = await _names_map(db, [item.product_id])
        return _build_item_response(item, names)

    async def complete_stocktake(
        self, db: AsyncSession, business_id: uuid.UUID, stocktake_id: uuid.UUID
    ) -> StocktakeResponse:
        stocktake = await db.scalar(
            select(Stocktake)
            .options(selectinload(Stocktake.items))
            .where(
                Stocktake.id == stocktake_id,
                Stocktake.business_id == business_id,
            )
        )
        if stocktake is None:
            raise NotFoundError("Stocktake not found")
        if stocktake.status == StocktakeStatus.completed:
            raise BadRequestError("Stocktake is already completed")

        # Calibrate stock for every checked item
        for item in stocktake.items:
            if not item.is_checked or item.actual_quantity is None:
                continue

            stock = await db.scalar(
                select(Stock).where(
                    Stock.product_id == item.product_id,
                    Stock.location_id == stocktake.location_id,
                )
            )
            if stock is None:
                stock = Stock(
                    product_id=item.product_id,
                    location_id=stocktake.location_id,
                    quantity=Decimal("0"),
                )
                db.add(stock)
                await db.flush()

            stock.quantity = _to_d(item.actual_quantity)

        stocktake.status = StocktakeStatus.completed
        stocktake.completed_at = datetime.now(timezone.utc)
        await db.commit()

        stocktake = await db.scalar(
            select(Stocktake)
            .options(selectinload(Stocktake.items))
            .where(Stocktake.id == stocktake_id)
        )
        names = await _names_map(db, [i.product_id for i in stocktake.items])
        return _build_stocktake_response(stocktake, names)


stocktake_service = StocktakeService()
