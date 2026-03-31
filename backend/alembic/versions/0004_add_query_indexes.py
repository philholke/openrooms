"""add query performance indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Waitlist queries filter by venue_id + status, ordered by check_in_time
    op.create_index(
        "ix_waitlist_venue_status",
        "waitlist_entries",
        ["venue_id", "status"],
    )

    # Reservation list/filter queries on venue + status
    op.create_index(
        "ix_reservation_venue_status",
        "reservations",
        ["venue_id", "status"],
    )

    # Guest profile lookups by reservation → guest_id
    op.create_index(
        "ix_reservation_guest_id",
        "reservations",
        ["guest_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_reservation_guest_id", table_name="reservations")
    op.drop_index("ix_reservation_venue_status", table_name="reservations")
    op.drop_index("ix_waitlist_venue_status", table_name="waitlist_entries")
