import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Currency, Language, Plan, UserRole


class BusinessResponse(BaseModel):
    id: uuid.UUID
    name: str
    currency: Currency
    language: Language
    plan: Plan
    max_locations: int
    max_products: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: str | None = None
    currency: Currency | None = None
    language: Language | None = None


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    location_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployeeUpdate(BaseModel):
    role: UserRole | None = None
    location_id: uuid.UUID | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def role_not_owner(cls, v: UserRole | None) -> UserRole | None:
        if v == UserRole.owner:
            raise ValueError("Cannot assign the owner role to an employee")
        return v


# Legacy aliases
BusinessBase = BusinessResponse
BusinessCreate = BusinessResponse
BusinessRead = BusinessResponse
