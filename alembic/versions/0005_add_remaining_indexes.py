"""add remaining indexes

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-11

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_users_business_id", "users", ["business_id"])
    op.create_index("ix_users_location_id", "users", ["location_id"])
    op.create_index("ix_locations_business_id", "locations", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_locations_business_id", table_name="locations")
    op.drop_index("ix_users_location_id", table_name="users")
    op.drop_index("ix_users_business_id", table_name="users")
