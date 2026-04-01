"""add missing FK indexes for query performance

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FK indexes missing from previous migrations.
    # These columns are frequently filtered/joined but lacked indexes,
    # causing sequential scans on large tables.
    op.create_index("ix_venues_org_id", "venues", ["org_id"])
    op.create_index("ix_floor_plans_venue_id", "floor_plans", ["venue_id"])
    op.create_index("ix_tables_floor_plan_id", "tables", ["floor_plan_id"])
    op.create_index("ix_access_rules_venue_id", "access_rules", ["venue_id"])
    op.create_index("ix_reservations_table_id", "reservations", ["table_id"])
    op.create_index("ix_reservations_access_rule_id", "reservations", ["access_rule_id"])
    op.create_index("ix_waitlist_entries_guest_id", "waitlist_entries", ["guest_id"])
    op.create_index("ix_guest_visits_reservation_id", "guest_visits", ["reservation_id"])


def downgrade() -> None:
    op.drop_index("ix_guest_visits_reservation_id", table_name="guest_visits")
    op.drop_index("ix_waitlist_entries_guest_id", table_name="waitlist_entries")
    op.drop_index("ix_reservations_access_rule_id", table_name="reservations")
    op.drop_index("ix_reservations_table_id", table_name="reservations")
    op.drop_index("ix_access_rules_venue_id", table_name="access_rules")
    op.drop_index("ix_tables_floor_plan_id", table_name="tables")
    op.drop_index("ix_floor_plans_venue_id", table_name="floor_plans")
    op.drop_index("ix_venues_org_id", table_name="venues")
