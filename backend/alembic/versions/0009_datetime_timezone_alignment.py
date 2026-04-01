"""align all datetime columns to use timezone=True

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All (table, column) pairs that need TIMESTAMP → TIMESTAMPTZ
_COLUMNS = [
    # organizations
    ("organizations", "created_at"),
    ("organizations", "updated_at"),
    # users
    ("users", "created_at"),
    ("users", "updated_at"),
    # venues
    ("venues", "created_at"),
    ("venues", "updated_at"),
    # tags
    ("tags", "created_at"),
    ("tags", "updated_at"),
    # guest_profiles
    ("guest_profiles", "created_at"),
    ("guest_profiles", "updated_at"),
    # guest_tags
    ("guest_tags", "created_at"),
    # floor_plans
    ("floor_plans", "created_at"),
    ("floor_plans", "updated_at"),
    # tables
    ("tables", "created_at"),
    ("tables", "updated_at"),
    # access_rules
    ("access_rules", "created_at"),
    ("access_rules", "updated_at"),
    # reservations
    ("reservations", "cancelled_at"),
    ("reservations", "created_at"),
    ("reservations", "updated_at"),
    # waitlist_entries
    ("waitlist_entries", "check_in_time"),
    ("waitlist_entries", "seated_time"),
    ("waitlist_entries", "created_at"),
    ("waitlist_entries", "updated_at"),
    # guest_visits
    ("guest_visits", "visited_at"),
    ("guest_visits", "created_at"),
    ("guest_visits", "updated_at"),
    # surveys
    ("surveys", "created_at"),
    ("surveys", "updated_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True if column not in ("created_at", "updated_at", "check_in_time") else False,
        )


def downgrade() -> None:
    for table, column in reversed(_COLUMNS):
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True if column not in ("created_at", "updated_at", "check_in_time") else False,
        )
