"""add auth indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-11

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users.email already has a UNIQUE constraint (which creates an index)
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=False)
    op.create_index("ix_users_invite_token", "users", ["invite_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_invite_token", table_name="users")
    op.drop_index("ix_users_google_id", table_name="users")
