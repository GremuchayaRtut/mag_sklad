import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


# ── ORM read schemas ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    business_id: uuid.UUID | None
    location_id: uuid.UUID | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Keep backward-compat aliases used by other schemas/__init__
class UserRead(UserResponse):
    updated_at: datetime


# ── Request / response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=6)]
    full_name: Annotated[str, Field(min_length=2)]


class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    id_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class InviteRequest(BaseModel):
    email: EmailStr
    role: UserRole
    location_id: uuid.UUID | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "staff@example.com", "role": "cashier"}]
        }
    }


class AcceptInviteRequest(BaseModel):
    token: str
    full_name: Annotated[str, Field(min_length=2)]
    password: Annotated[str, Field(min_length=6)]


# ── Mutation schemas (kept for future CRUD endpoints) ─────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    password: str | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    location_id: uuid.UUID | None = None
