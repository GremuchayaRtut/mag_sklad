import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import Currency, Language, Plan

if TYPE_CHECKING:
    from app.models.user import User


class Business(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    currency: Mapped[Currency] = mapped_column(default=Currency.TJS, nullable=False)
    language: Mapped[Language] = mapped_column(default=Language.ru, nullable=False)
    plan: Mapped[Plan] = mapped_column(default=Plan.trial, nullable=False)
    max_locations: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_products: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], back_populates="owned_business")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="business")  # noqa: F821
    users: Mapped[list["User"]] = relationship("User", foreign_keys="User.business_id", back_populates="business")
