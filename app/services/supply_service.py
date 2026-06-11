import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enums import SupplyStatus
from app.models.location import Location
from app.models.product import Product
from app.models.stock import Stock
from app.models.supply import Supply, SupplyItem
from app.schemas.supply import (
    SupplyCreate,
    SupplyItemResponse,
    SupplyListResponse,
    SupplyResponse,
)


# ── Shared helper ─────────────────────────────────────────────────────────────

async def _names_map(db: AsyncSession, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not product_ids:
        return {}
    rows = await db.execute(
        select(Product.id, Product.name).where(Product.id.in_(product_ids))
    )
    return {row[0]: row[1] for row in rows}


def _to_d(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _build_supply_response(supply: Supply, names: dict[uuid.UUID, str]) -> SupplyResponse:
    return SupplyResponse(
        id=supply.id,
        location_id=supply.location_id,
        supplier_name=supply.supplier_name,
        invoice_number=supply.invoice_number,
        status=supply.status,
        supply_date=supply.supply_date,
        note=supply.note,
        created_at=supply.created_at,
        items=[
            SupplyItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=names.get(item.product_id, ""),
                quantity=_to_d(item.quantity),
                purchase_price=_to_d(item.purchase_price),
            )
            for item in supply.items
        ],
    )


# ── Service ───────────────────────────────────────────────────────────────────

class SupplyService:

    async def get_supplies(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        *,
        location_id: uuid.UUID | None = None,
        status: SupplyStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> SupplyListResponse:
        conditions = [Supply.business_id == business_id]
        if location_id:
            conditions.append(Supply.location_id == location_id)
        if status:
            conditions.append(Supply.status == status)

        total: int = (
            await db.scalar(
                select(func.count(Supply.id)).where(*conditions)
            )
        ) or 0

        rows = (
            await db.execute(
                select(Supply)
                .options(selectinload(Supply.items))
                .where(*conditions)
                .order_by(Supply.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        # Batch-load product names for all items across all supplies
        all_product_ids = list({item.product_id for s in rows for item in s.items})
        names = await _names_map(db, all_product_ids)

        return SupplyListResponse(
            items=[_build_supply_response(s, names) for s in rows],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_supply_by_id(
        self, db: AsyncSession, business_id: uuid.UUID, supply_id: uuid.UUID
    ) -> SupplyResponse:
        supply = await db.scalar(
            select(Supply)
            .options(selectinload(Supply.items))
            .where(Supply.id == supply_id, Supply.business_id == business_id)
        )
        if supply is None:
            raise NotFoundError("Supply not found")

        names = await _names_map(db, [item.product_id for item in supply.items])
        return _build_supply_response(supply, names)

    async def create_supply(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        created_by_id: uuid.UUID,
        data: SupplyCreate,
    ) -> SupplyResponse:
        location = await db.scalar(
            select(Location).where(
                Location.id == data.location_id,
                Location.business_id == business_id,
            )
        )
        if location is None:
            raise BadRequestError("Location not found or does not belong to this business")

        supply = Supply(
            business_id=business_id,
            location_id=data.location_id,
            created_by=created_by_id,
            supplier_name=data.supplier_name,
            invoice_number=data.invoice_number,
            status=SupplyStatus.draft,
            note=data.note,
            supply_date=data.supply_date,
        )
        db.add(supply)
        await db.flush()

        product_ids = [item.product_id for item in data.items]
        for item_data in data.items:
            db.add(
                SupplyItem(
                    supply_id=supply.id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    purchase_price=item_data.purchase_price,
                )
            )

        await db.commit()
        await db.refresh(supply)

        # Re-load with items relationship populated
        supply = await db.scalar(
            select(Supply)
            .options(selectinload(Supply.items))
            .where(Supply.id == supply.id)
        )
        names = await _names_map(db, product_ids)
        return _build_supply_response(supply, names)

    async def confirm_supply(
        self, db: AsyncSession, business_id: uuid.UUID, supply_id: uuid.UUID
    ) -> SupplyResponse:
        supply = await db.scalar(
            select(Supply)
            .options(selectinload(Supply.items))
            .where(Supply.id == supply_id, Supply.business_id == business_id)
        )
        if supply is None:
            raise NotFoundError("Supply not found")
        if supply.status == SupplyStatus.confirmed:
            raise BadRequestError("Supply is already confirmed")

        # All stock updates happen before the single commit — fully atomic
        for item in supply.items:
            stock = await db.scalar(
                select(Stock).where(
                    Stock.product_id == item.product_id,
                    Stock.location_id == supply.location_id,
                )
            )
            if stock is None:
                stock = Stock(
                    product_id=item.product_id,
                    location_id=supply.location_id,
                    quantity=Decimal("0"),
                )
                db.add(stock)
                await db.flush()

            stock.quantity = _to_d(stock.quantity) + _to_d(item.quantity)

            # Latest purchase price wins
            product = await db.scalar(
                select(Product).where(Product.id == item.product_id)
            )
            if product is not None:
                product.purchase_price = item.purchase_price

        supply.status = SupplyStatus.confirmed
        await db.commit()

        supply = await db.scalar(
            select(Supply)
            .options(selectinload(Supply.items))
            .where(Supply.id == supply_id)
        )
        names = await _names_map(db, [item.product_id for item in supply.items])
        return _build_supply_response(supply, names)

    async def delete_supply(
        self, db: AsyncSession, business_id: uuid.UUID, supply_id: uuid.UUID
    ) -> None:
        supply = await db.scalar(
            select(Supply)
            .options(selectinload(Supply.items))
            .where(Supply.id == supply_id, Supply.business_id == business_id)
        )
        if supply is None:
            raise NotFoundError("Supply not found")
        if supply.status == SupplyStatus.confirmed:
            raise BadRequestError("Cannot delete a confirmed supply")

        for item in supply.items:
            await db.delete(item)
        await db.delete(supply)
        await db.commit()


supply_service = SupplyService()
