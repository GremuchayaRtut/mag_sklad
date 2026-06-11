import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from app.models.base import Base, UUIDMixin
from app.models.enums import StocktakeStatus


class Stocktake(UUIDMixin, Base):
    __tablename__ = "stocktakes"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[StocktakeStatus] = mapped_column(
        default=StocktakeStatus.in_progress, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list["StocktakeItem"]] = relationship("StocktakeItem", back_populates="stocktake")


class StocktakeItem(UUIDMixin, Base):
    __tablename__ = "stocktake_items"

    stocktake_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stocktakes.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    expected_quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    actual_quantity: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    stocktake: Mapped[Stocktake] = relationship("Stocktake", back_populates="items")
