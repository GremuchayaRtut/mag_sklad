from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_manager_or_above, get_current_user, get_db
from app.core.exceptions import BadRequestError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import (
    AcceptInviteRequest,
    GoogleAuthRequest,
    InviteRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user, access_token, refresh_token = await auth_service.register(
        db, body.email, body.password, body.full_name
    )
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2PasswordRequestForm uses `username` field for email
    user, access_token, refresh_token = await auth_service.login(
        db, form.username, form.password
    )
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/google", response_model=LoginResponse)
async def google_auth(
    body: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    user, access_token, refresh_token = await auth_service.google_auth(db, body.id_token)
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    access_token, refresh_token = await auth_service.refresh_tokens(db, body.refresh_token)
    return RefreshResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/invite", status_code=200)
async def invite_employee(
    body: InviteRequest,
    current_user: User = Depends(get_current_manager_or_above),
    db: AsyncSession = Depends(get_db),
):
    if body.role == UserRole.owner:
        raise BadRequestError("Cannot invite another owner")

    if current_user.business_id is None:
        raise BadRequestError("User has no associated business")

    await auth_service.invite_employee(
        db=db,
        business_id=current_user.business_id,
        invited_by_user=current_user,
        email=body.email,
        role=body.role,
        location_id=body.location_id,
    )
    return {"message": "Приглашение отправлено"}


@router.post("/invite/accept", response_model=LoginResponse)
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    user, access_token, refresh_token = await auth_service.accept_invite(
        db, body.token, body.full_name, body.password
    )
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=200)
async def logout():
    # JWT tokens are stateless; client discards tokens on their side.
    # TODO: implement token blocklist (Redis) if revocation is needed.
    return {"message": "Logged out successfully"}
