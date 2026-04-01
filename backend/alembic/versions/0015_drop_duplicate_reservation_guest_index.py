"""Drop duplicate index on reservations.guest_id.

Migration 0004 created ix_reservation_guest_id and migration 0014
created ix_reservations_guest_id on the same column. This removes
the redundant 0014 index.

Revision ID: 0015
Revises: 0014
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_reservations_guest_id", table_name="reservations")


def downgrade() -> None:
    op.create_index("ix_reservations_guest_id", "reservations", ["guest_id"])
