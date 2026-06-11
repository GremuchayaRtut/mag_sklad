"""add product indexes

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-11

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_products_business_id", "products", ["business_id"])
    op.create_index("ix_products_barcode", "products", ["barcode"])
    op.create_index("ix_products_internal_barcode", "products", ["internal_barcode"])
    op.create_index("ix_stock_product_id", "stock", ["product_id"])
    op.create_index("ix_stock_location_id", "stock", ["location_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_location_id", table_name="stock")
    op.drop_index("ix_stock_product_id", table_name="stock")
    op.drop_index("ix_products_internal_barcode", table_name="products")
    op.drop_index("ix_products_barcode", table_name="products")
    op.drop_index("ix_products_business_id", table_name="products")
