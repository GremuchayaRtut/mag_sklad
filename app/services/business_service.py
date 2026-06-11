import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.business import Business
from app.models.enums import Currency, Language, UserRole
from app.models.user import User
from app.schemas.business import BusinessResponse, EmployeeResponse


class BusinessService:

    async def get_business(
        self, db: AsyncSession, business_id: uuid.UUID
    ) -> BusinessResponse:
        business = await db.scalar(
            select(Business).where(Business.id == business_id)
        )
        if business is None:
            raise NotFoundError("Business not found")
        return BusinessResponse.model_validate(business)

    async def update_business(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        *,
        name: str | None = None,
        currency: Currency | None = None,
        language: Language | None = None,
    ) -> BusinessResponse:
        business = await db.scalar(
            select(Business).where(Business.id == business_id)
        )
        if business is None:
            raise NotFoundError("Business not found")

        if name is not None:
            business.name = name
        if currency is not None:
            business.currency = currency
        if language is not None:
            business.language = language

        await db.commit()
        await db.refresh(business)
        return BusinessResponse.model_validate(business)

    async def get_employees(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        location_id: uuid.UUID | None = None,
    ) -> list[EmployeeResponse]:
        conditions = [
            User.business_id == business_id,
            User.role != UserRole.owner,
        ]
        if location_id:
            conditions.append(User.location_id == location_id)

        rows = (
            await db.execute(
                select(User)
                .where(*conditions)
                .order_by(User.full_name)
            )
        ).scalars().all()
        return [EmployeeResponse.model_validate(u) for u in rows]

    async def update_employee(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        role: UserRole | None = None,
        location_id: uuid.UUID | None = None,
        is_active: bool | None = None,
    ) -> EmployeeResponse:
        user = await db.scalar(
            select(User).where(
                User.id == user_id,
                User.business_id == business_id,
            )
        )
        if user is None:
            raise NotFoundError("Employee not found")
        if role == UserRole.owner:
            raise BadRequestError("Cannot assign the owner role to an employee")

        if role is not None:
            user.role = role
        if location_id is not None:
            user.location_id = location_id
        if is_active is not None:
            user.is_active = is_active

        await db.commit()
        await db.refresh(user)
        return EmployeeResponse.model_validate(user)

    async def remove_employee(
        self, db: AsyncSession, business_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        user = await db.scalar(
            select(User).where(
                User.id == user_id,
                User.business_id == business_id,
            )
        )
        if user is None:
            raise NotFoundError("Employee not found")
        if user.role == UserRole.owner:
            raise BadRequestError("Cannot remove the business owner")

        user.is_active = False
        await db.commit()


business_service = BusinessService()
