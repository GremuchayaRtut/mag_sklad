import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    make_token_payload,
    verify_password,
)
from app.models.business import Business
from app.models.enums import Plan, UserRole
from app.models.user import User
from app.utils.telegram import notify_new_registration


def _hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _make_tokens(user: User) -> tuple[str, str]:
    payload = make_token_payload(user.id, user.role.value, user.business_id)
    return create_access_token(payload), create_refresh_token(payload)


class AuthService:
    # ── Registration ──────────────────────────────────────────────────────────

    async def register(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
    ) -> tuple[User, str, str]:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            raise BadRequestError("Email already registered")

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.owner,
            is_active=True,
        )
        db.add(user)
        await db.flush()  # get user.id without committing

        business_name = f"{full_name}'s Business"
        business = Business(
            name=business_name,
            owner_id=user.id,
            plan=Plan.trial,
        )
        db.add(business)
        await db.flush()

        user.business_id = business.id
        await db.commit()
        await db.refresh(user)

        access_token, refresh_token = _make_tokens(user)
        await notify_new_registration(user.email, business_name)
        return user, access_token, refresh_token

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> tuple[User, str, str]:
        user = await db.scalar(select(User).where(User.email == email))
        if user is None or not user.hashed_password:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("Account is disabled")

        access_token, refresh_token = _make_tokens(user)
        return user, access_token, refresh_token

    # ── Google OAuth ──────────────────────────────────────────────────────────

    async def google_auth(
        self, db: AsyncSession, google_token: str
    ) -> tuple[User, str, str]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": google_token},
            )

        if resp.status_code != 200:
            raise UnauthorizedError("Invalid Google token")

        info = resp.json()
        google_id: str = info.get("sub", "")
        email: str = info.get("email", "")
        full_name: str = info.get("name", email)
        avatar_url: str | None = info.get("picture")

        if not google_id or not email:
            raise UnauthorizedError("Google token missing required fields")

        # 1. Known by google_id
        user = await db.scalar(select(User).where(User.google_id == google_id))

        if user is None:
            # 2. Known by email — link account
            user = await db.scalar(select(User).where(User.email == email))
            if user is not None:
                user.google_id = google_id
                if avatar_url:
                    user.avatar_url = avatar_url
                await db.commit()
                await db.refresh(user)

        if user is None:
            # 3. Brand-new user
            user = User(
                email=email,
                full_name=full_name,
                google_id=google_id,
                avatar_url=avatar_url,
                role=UserRole.owner,
                is_active=True,
            )
            db.add(user)
            await db.flush()

            business_name = f"{full_name}'s Business"
            business = Business(
                name=business_name,
                owner_id=user.id,
                plan=Plan.trial,
            )
            db.add(business)
            await db.flush()

            user.business_id = business.id
            await db.commit()
            await db.refresh(user)
            await notify_new_registration(user.email, business_name)

        access_token, refresh_token = _make_tokens(user)
        return user, access_token, refresh_token

    # ── Token refresh ─────────────────────────────────────────────────────────

    async def refresh_tokens(
        self, db: AsyncSession, refresh_token: str
    ) -> tuple[str, str]:
        from app.core.security import decode_token

        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid or expired refresh token")

        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedError("Invalid token payload")

        user = await db.scalar(
            select(User).where(User.id == uuid.UUID(user_id_str))
        )
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or disabled")

        new_payload = make_token_payload(user.id, user.role.value, user.business_id)
        return create_access_token(new_payload), create_refresh_token(new_payload)

    # ── Invite employee ───────────────────────────────────────────────────────

    async def invite_employee(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        invited_by_user: User,
        email: str,
        role: UserRole,
        location_id: uuid.UUID | None = None,
    ) -> User:
        if role == UserRole.owner:
            raise BadRequestError("Cannot invite another owner")

        # TODO: check business employee/location limits when billing is implemented

        duplicate = await db.scalar(
            select(User).where(User.email == email, User.business_id == business_id)
        )
        if duplicate:
            raise BadRequestError("User with this email already belongs to this business")

        raw_token = secrets.token_urlsafe(32)
        hashed_token = _hash_invite_token(raw_token)

        employee = User(
            email=email,
            business_id=business_id,
            location_id=location_id,
            role=role,
            full_name="",  # set on accept
            is_active=False,
            invited_by=invited_by_user.id,
            invite_token=hashed_token,
            invite_expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)

        from app.utils.email import send_invite_email

        business = await db.scalar(
            select(Business).where(Business.id == business_id)
        )
        await send_invite_email(
            to_email=email,
            invite_token=raw_token,  # send raw token; DB stores hash
            inviter_name=invited_by_user.full_name,
            business_name=business.name if business else "",
        )
        return employee

    # ── Accept invite ─────────────────────────────────────────────────────────

    async def accept_invite(
        self,
        db: AsyncSession,
        token: str,
        full_name: str,
        password: str,
    ) -> tuple[User, str, str]:
        hashed = _hash_invite_token(token)
        user = await db.scalar(
            select(User).where(User.invite_token == hashed)
        )

        now = datetime.now(timezone.utc)

        if user is None:
            raise BadRequestError("Invalid invite token")
        if user.is_active:
            raise BadRequestError("Invite already accepted")
        if user.invite_expires_at is None or user.invite_expires_at.replace(tzinfo=timezone.utc) < now:
            raise BadRequestError("Invite token has expired")

        user.full_name = full_name
        user.hashed_password = get_password_hash(password)
        user.is_active = True
        user.invite_token = None
        user.invite_expires_at = None

        await db.commit()
        await db.refresh(user)

        access_token, refresh_token = _make_tokens(user)
        return user, access_token, refresh_token


auth_service = AuthService()
