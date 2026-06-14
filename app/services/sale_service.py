import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enums import SaleStatus
from app.models.location import Location
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.stock import Stock
from app.schemas.sale import (
    SaleCreate,
    SaleItemResponse,
    SaleListResponse,
    SaleResponse,
    SalesSummary,
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


def _build_sale_response(sale: Sale, names: dict[uuid.UUID, str]) -> SaleResponse:
    return SaleResponse(
        id=sale.id,
        location_id=sale.location_id,
        status=sale.status,
        total_amount=_to_d(sale.total_amount),
        total_cost=_to_d(sale.total_cost),
        note=sale.note,
        created_at=sale.created_at,
        items=[
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=names.get(item.product_id, ""),
                quantity=_to_d(item.quantity),
                sale_price=_to_d(item.sale_price),
                purchase_price=_to_d(item.purchase_price),
            )
            for item in sale.items
        ],
    )


class SaleService:

    async def get_sales(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        *,
        location_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> SaleListResponse:
        conditions = [Sale.business_id == business_id]
        if location_id:
            conditions.append(Sale.location_id == location_id)

        total: int = (
            await db.scalar(select(func.count(Sale.id)).where(*conditions))
        ) or 0

        rows = (
            await db.execute(
                select(Sale)
                .options(selectinload(Sale.items))
                .where(*conditions)
                .order_by(Sale.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        all_product_ids = list({item.product_id for s in rows for item in s.items})
        names = await _names_map(db, all_product_ids)

        return SaleListResponse(
            items=[_build_sale_response(s, names) for s in rows],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_sale_by_id(
        self, db: AsyncSession, business_id: uuid.UUID, sale_id: uuid.UUID
    ) -> SaleResponse:
        sale = await db.scalar(
            select(Sale)
            .options(selectinload(Sale.items))
            .where(Sale.id == sale_id, Sale.business_id == business_id)
        )
        if sale is None:
            raise NotFoundError("Sale not found")

        names = await _names_map(db, [item.product_id for item in sale.items])
        return _build_sale_response(sale, names)

    async def create_sale(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        location_id: uuid.UUID,
        created_by_id: uuid.UUID,
        data: SaleCreate,
    ) -> SaleResponse:
        location = await db.scalar(
            select(Location).where(
                Location.id == location_id,
                Location.business_id == business_id,
            )
        )
        if location is None:
            raise BadRequestError("Location not found or does not belong to this business")

        # ── Phase 1: validate all items before touching anything ──────────────
        validated: list[tuple[Product, Stock, Decimal]] = []

        for item_input in data.items:
            product = await db.scalar(
                select(Product).where(
                    Product.id == item_input.product_id,
                    Product.business_id == business_id,
                    Product.is_active.is_(True),
                )
            )
            if product is None:
                raise NotFoundError(
                    f"Product {item_input.product_id} not found"
                )

            stock = await db.scalar(
                select(Stock).where(
                    Stock.product_id == item_input.product_id,
                    Stock.location_id == location_id,
                )
            )
            available = _to_d(stock.quantity) if stock else Decimal("0")
            qty = _to_d(item_input.quantity)

            if available < qty:
                raise BadRequestError(
                    f"Insufficient stock for '{product.name}': "
                    f"available {available}, requested {qty}"
                )

            validated.append((product, stock, qty))

        # ── Phase 2: write (only reached when all checks pass) ────────────────
        total_amount = Decimal("0")
        total_cost = Decimal("0")
        sale_items_data: list[dict] = []

        for product, stock, qty in validated:
            sale_price = _to_d(product.sale_price)
            purchase_price = _to_d(product.purchase_price)

            total_amount += qty * sale_price
            total_cost += qty * purchase_price

            sale_items_data.append(
                {
                    "product_id": product.id,
                    "quantity": qty,
                    "sale_price": sale_price,
                    "purchase_price": purchase_price,
                }
            )
            stock.quantity = _to_d(stock.quantity) - qty

        sale = Sale(
            business_id=business_id,
            location_id=location_id,
            created_by=created_by_id,
            status=SaleStatus.completed,
            total_amount=total_amount,
            total_cost=total_cost,
            note=data.note,
        )
        db.add(sale)
        await db.flush()

        for item_data in sale_items_data:
            db.add(SaleItem(sale_id=sale.id, **item_data))

        await db.commit()

        sale = await db.scalar(
            select(Sale)
            .options(selectinload(Sale.items))
            .where(Sale.id == sale.id)
        )
        names = await _names_map(db, [d["product_id"] for d in sale_items_data])
        return _build_sale_response(sale, names)

    async def cancel_sale(
        self, db: AsyncSession, business_id: uuid.UUID, sale_id: uuid.UUID
    ) -> SaleResponse:
        sale = await db.scalar(
            select(Sale)
            .options(selectinload(Sale.items))
            .where(Sale.id == sale_id, Sale.business_id == business_id)
        )
        if sale is None:
            raise NotFoundError("Sale not found")
        if sale.status == SaleStatus.cancelled:
            raise BadRequestError("Sale is already cancelled")

        for item in sale.items:
            stock = await db.scalar(
                select(Stock).where(
                    Stock.product_id == item.product_id,
                    Stock.location_id == sale.location_id,
                )
            )
            if stock is not None:
                stock.quantity = _to_d(stock.quantity) + _to_d(item.quantity)

        sale.status = SaleStatus.cancelled
        await db.commit()

        names = await _names_map(db, [item.product_id for item in sale.items])
        return _build_sale_response(sale, names)

    async def get_sales_summary(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        *,
        location_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> SalesSummary:
        conditions = [
            Sale.business_id == business_id,
            Sale.status == SaleStatus.completed,
        ]
        if location_id:
            conditions.append(Sale.location_id == location_id)
        if date_from:
            conditions.append(func.date(Sale.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(Sale.created_at) <= date_to)

        row = (
            await db.execute(
                select(
                    func.coalesce(func.sum(Sale.total_amount), 0).label("revenue"),
                    func.coalesce(func.sum(Sale.total_cost), 0).label("cost"),
                    func.count(Sale.id).label("cnt"),
                ).where(*conditions)
            )
        ).one()

        revenue = _to_d(row.revenue)
        cost = _to_d(row.cost)
        profit = revenue - cost
        cnt = int(row.cnt)
        margin = (
            (profit / revenue * 100).quantize(Decimal("0.01"))
            if revenue > 0
            else Decimal("0.00")
        )
        average = (revenue / cnt).quantize(Decimal("0.01")) if cnt > 0 else Decimal("0.00")

        return SalesSummary(
            total_revenue=revenue,
            total_cost=cost,
            total_profit=profit,
            profit_margin=margin,
            sales_count=cnt,
            average_sale=average,
            date_from=date_from,
            date_to=date_to,
        )


sale_service = SaleService()
