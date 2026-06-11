import uuid

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.business import Business
from app.models.location import Location
from app.models.product import Product
from app.models.stock import Stock
from app.schemas.location import LocationResponse


def _response(loc: Location) -> LocationResponse:
    return LocationResponse.model_validate(loc)


class LocationService:

    async def get_locations(
        self, db: AsyncSession, business_id: uuid.UUID
    ) -> list[LocationResponse]:
        rows = (
            await db.execute(
                select(Location)
                .where(Location.business_id == business_id)
                .order_by(Location.name)
            )
        ).scalars().all()
        return [_response(loc) for loc in rows]

    async def get_location_by_id(
        self, db: AsyncSession, business_id: uuid.UUID, location_id: uuid.UUID
    ) -> LocationResponse:
        loc = await db.scalar(
            select(Location).where(
                Location.id == location_id,
                Location.business_id == business_id,
            )
        )
        if loc is None:
            raise NotFoundError("Location not found")
        return _response(loc)

    async def create_location(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        name: str,
        address: str | None = None,
        currency=None,
    ) -> LocationResponse:
        business = await db.scalar(
            select(Business).where(Business.id == business_id)
        )
        if business is None:
            raise NotFoundError("Business not found")

        active_count: int = (
            await db.scalar(
                select(func.count(Location.id)).where(
                    Location.business_id == business_id,
                    Location.is_active.is_(True),
                )
            )
        ) or 0

        if active_count >= business.max_locations:
            raise BadRequestError(
                f"Location limit reached. Current plan allows "
                f"{business.max_locations} location(s)."
            )

        loc = Location(
            business_id=business_id,
            name=name,
            address=address,
            currency=currency,
            is_active=True,
        )
        db.add(loc)
        await db.flush()

        # Bulk-insert stock=0 for every active product so the new location
        # immediately appears in inventory for all existing products.
        product_ids = (
            await db.execute(
                select(Product.id).where(
                    Product.business_id == business_id,
                    Product.is_active.is_(True),
                )
            )
        ).scalars().all()

        if product_ids:
            await db.execute(
                insert(Stock),
                [
                    {
                        "id": uuid.uuid4(),
                        "product_id": pid,
                        "location_id": loc.id,
                        "quantity": 0,
                    }
                    for pid in product_ids
                ],
            )

        await db.commit()
        await db.refresh(loc)
        return _response(loc)

    async def update_location(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        location_id: uuid.UUID,
        *,
        name: str | None = None,
        address: str | None = None,
        currency=None,
        is_active: bool | None = None,
    ) -> LocationResponse:
        loc = await db.scalar(
            select(Location).where(
                Location.id == location_id,
                Location.business_id == business_id,
            )
        )
        if loc is None:
            raise NotFoundError("Location not found")

        if name is not None:
            loc.name = name
        if address is not None:
            loc.address = address
        if currency is not None:
            loc.currency = currency
        if is_active is not None:
            loc.is_active = is_active

        await db.commit()
        await db.refresh(loc)
        return _response(loc)

    async def delete_location(
        self, db: AsyncSession, business_id: uuid.UUID, location_id: uuid.UUID
    ) -> None:
        loc = await db.scalar(
            select(Location).where(
                Location.id == location_id,
                Location.business_id == business_id,
            )
        )
        if loc is None:
            raise NotFoundError("Location not found")

        active_count: int = (
            await db.scalar(
                select(func.count(Location.id)).where(
                    Location.business_id == business_id,
                    Location.is_active.is_(True),
                )
            )
        ) or 0

        if active_count <= 1:
            raise BadRequestError("Cannot deactivate the only active location")

        loc.is_active = False
        await db.commit()


location_service = LocationService()
