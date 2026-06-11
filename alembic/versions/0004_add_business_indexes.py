"""add business module indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-11

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_supplies_business_id", "supplies", ["business_id"])
    op.create_index("ix_supplies_location_id", "supplies", ["location_id"])
    op.create_index("ix_supplies_status", "supplies", ["status"])
    op.create_index("ix_sales_business_id", "sales", ["business_id"])
    op.create_index("ix_sales_location_id", "sales", ["location_id"])
    op.create_index("ix_sales_created_at", "sales", ["created_at"])
    op.create_index("ix_stocktakes_business_id", "stocktakes", ["business_id"])
    op.create_index("ix_stocktakes_location_id", "stocktakes", ["location_id"])


def downgrade() -> None:
    op.drop_index("ix_stocktakes_location_id", table_name="stocktakes")
    op.drop_index("ix_stocktakes_business_id", table_name="stocktakes")
    op.drop_index("ix_sales_created_at", table_name="sales")
    op.drop_index("ix_sales_location_id", table_name="sales")
    op.drop_index("ix_sales_business_id", table_name="sales")
    op.drop_index("ix_supplies_status", table_name="supplies")
    op.drop_index("ix_supplies_location_id", table_name="supplies")
    op.drop_index("ix_supplies_business_id", table_name="supplies")
