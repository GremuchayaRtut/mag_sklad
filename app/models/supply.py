import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import SupplyStatus


class Supply(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "supplies"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[SupplyStatus] = mapped_column(default=SupplyStatus.draft, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    supply_date: Mapped[date] = mapped_column(Date, nullable=False)

    items: Mapped[list["SupplyItem"]] = relationship("SupplyItem", back_populates="supply")


class SupplyItem(UUIDMixin, Base):
    __tablename__ = "supply_items"

    supply_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplies.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    supply: Mapped[Supply] = relationship("Supply", back_populates="items")
