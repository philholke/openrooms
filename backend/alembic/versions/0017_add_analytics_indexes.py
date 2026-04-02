"""Add composite indexes for analytics query performance.

Revision ID: 0017
Revises: 0016
"""
from typing import Union

from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Reservation analytics: date-range queries with status filtering
    op.create_index(
        "ix_reservations_venue_date_status",
        "reservations",
        ["venue_id", "date", "status"],
    )

    # Reservation analytics: source breakdown
    op.create_index(
        "ix_reservations_venue_source",
        "reservations",
        ["venue_id", "source"],
    )

    # Guest analytics: new guest growth over time
    op.create_index(
        "ix_guest_profiles_org_created",
        "guest_profiles",
        ["org_id", "created_at"],
    )

    # Guest visit analytics: return rate, visit frequency
    op.create_index(
        "ix_guest_visits_guest_visited",
        "guest_visits",
        ["guest_id", "visited_at"],
    )

    # Waitlist analytics
    op.create_index(
        "ix_waitlist_entries_venue_status_created",
        "waitlist_entries",
        ["venue_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_venue_status_created", table_name="waitlist_entries")
    op.drop_index("ix_guest_visits_guest_visited", table_name="guest_visits")
    op.drop_index("ix_guest_profiles_org_created", table_name="guest_profiles")
    op.drop_index("ix_reservations_venue_source", table_name="reservations")
    op.drop_index("ix_reservations_venue_date_status", table_name="reservations")
