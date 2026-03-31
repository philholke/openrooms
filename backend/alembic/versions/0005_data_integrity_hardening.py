"""data integrity hardening: CHECK constraints, org slug partial index, FK indexes

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. Organization slug: partial unique index (mirrors users.email from 0003) ──
    op.drop_constraint("organizations_slug_key", "organizations", type_="unique")
    op.create_index(
        "ix_organizations_slug_active",
        "organizations",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    # ─── 2. CHECK constraints — survey ratings 1-5 ──────────────────────────
    op.create_check_constraint(
        "ck_surveys_overall_rating_range",
        "surveys",
        "overall_rating >= 1 AND overall_rating <= 5",
    )
    op.create_check_constraint(
        "ck_surveys_food_rating_range",
        "surveys",
        "food_rating IS NULL OR (food_rating >= 1 AND food_rating <= 5)",
    )
    op.create_check_constraint(
        "ck_surveys_service_rating_range",
        "surveys",
        "service_rating IS NULL OR (service_rating >= 1 AND service_rating <= 5)",
    )
    op.create_check_constraint(
        "ck_surveys_ambiance_rating_range",
        "surveys",
        "ambiance_rating IS NULL OR (ambiance_rating >= 1 AND ambiance_rating <= 5)",
    )
    op.create_check_constraint(
        "ck_surveys_drinks_rating_range",
        "surveys",
        "drinks_rating IS NULL OR (drinks_rating >= 1 AND drinks_rating <= 5)",
    )

    # ─── 3. CHECK constraint — table capacity min <= max ─────────────────────
    op.create_check_constraint(
        "ck_tables_capacity_range",
        "tables",
        "min_capacity <= max_capacity",
    )

    # ─── 4. CHECK constraints — access rule time and date ordering ───────────
    op.create_check_constraint(
        "ck_access_rules_time_order",
        "access_rules",
        "start_time < end_time",
    )
    op.create_check_constraint(
        "ck_access_rules_date_order",
        "access_rules",
        "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
    )

    # ─── 5. CHECK constraints — reservation and waitlist status enums ────────
    op.create_check_constraint(
        "ck_reservations_status",
        "reservations",
        "status IN ('pending', 'confirmed', 'arrived', 'partially_arrived', "
        "'seated', 'completed', 'no_show', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_waitlist_entries_status",
        "waitlist_entries",
        "status IN ('waiting', 'notified', 'seated', 'cancelled', 'no_show')",
    )

    # ─── 6. FK indexes for common query paths ───────────────────────────────
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_tags_org_id", "tags", ["org_id"])
    op.create_index("ix_guest_profiles_org_id", "guest_profiles", ["org_id"])
    op.create_index("ix_guest_visits_guest_id", "guest_visits", ["guest_id"])
    op.create_index("ix_guest_visits_venue_id", "guest_visits", ["venue_id"])


def downgrade() -> None:
    # FK indexes
    op.drop_index("ix_guest_visits_venue_id", table_name="guest_visits")
    op.drop_index("ix_guest_visits_guest_id", table_name="guest_visits")
    op.drop_index("ix_guest_profiles_org_id", table_name="guest_profiles")
    op.drop_index("ix_tags_org_id", table_name="tags")
    op.drop_index("ix_users_org_id", table_name="users")

    # Status CHECK constraints
    op.drop_constraint("ck_waitlist_entries_status", "waitlist_entries", type_="check")
    op.drop_constraint("ck_reservations_status", "reservations", type_="check")

    # Access rule CHECK constraints
    op.drop_constraint("ck_access_rules_date_order", "access_rules", type_="check")
    op.drop_constraint("ck_access_rules_time_order", "access_rules", type_="check")

    # Table capacity CHECK constraint
    op.drop_constraint("ck_tables_capacity_range", "tables", type_="check")

    # Survey rating CHECK constraints
    op.drop_constraint("ck_surveys_drinks_rating_range", "surveys", type_="check")
    op.drop_constraint("ck_surveys_ambiance_rating_range", "surveys", type_="check")
    op.drop_constraint("ck_surveys_service_rating_range", "surveys", type_="check")
    op.drop_constraint("ck_surveys_food_rating_range", "surveys", type_="check")
    op.drop_constraint("ck_surveys_overall_rating_range", "surveys", type_="check")

    # Org slug: restore unconditional unique constraint
    op.drop_index("ix_organizations_slug_active", table_name="organizations")
    op.create_unique_constraint("organizations_slug_key", "organizations", ["slug"])
