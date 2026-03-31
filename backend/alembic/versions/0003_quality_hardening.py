"""quality hardening: partial unique index on users.email, index on cancel_token

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Replace unconditional UNIQUE on users.email with a partial unique index
    #    so that soft-deleted users no longer block email reuse.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.create_index(
        "ix_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    # 2. Add explicit index on reservations.cancel_token for fast public cancel lookups.
    #    The column already has a UNIQUE constraint which implies an index in Postgres,
    #    but we add a named one for clarity and portability.
    op.create_index(
        "ix_reservations_cancel_token",
        "reservations",
        ["cancel_token"],
    )


def downgrade() -> None:
    op.drop_index("ix_reservations_cancel_token", table_name="reservations")
    op.drop_index("ix_users_email_active", table_name="users")
    op.create_unique_constraint("users_email_key", "users", ["email"])
