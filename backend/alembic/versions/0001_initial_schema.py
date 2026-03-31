"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    # --- venues ---
    op.create_table(
        "venues",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(100), server_default=sa.text("'UTC'"), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "slug", name="uq_venue_org_slug"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    # --- tags ---
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("is_auto", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_tag_org_name"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    # --- guest_profiles ---
    op.create_table(
        "guest_profiles",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("birthday", sa.Date(), nullable=True),
        sa.Column("anniversary", sa.Date(), nullable=True),
        sa.Column("dietary_restrictions", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "email", name="uq_guest_org_email"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    # --- guest_tags (association table) ---
    op.create_table(
        "guest_tags",
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("guest_id", "tag_id"),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
    )

    # --- floor_plans ---
    op.create_table(
        "floor_plans",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
    )

    # --- tables ---
    op.create_table(
        "tables",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("floor_plan_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("min_capacity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("x_position", sa.Float(), nullable=True),
        sa.Column("y_position", sa.Float(), nullable=True),
        sa.Column("shape", sa.String(50), server_default=sa.text("'rectangle'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_plan_id"], ["floor_plans.id"], ondelete="CASCADE"),
    )

    # --- access_rules ---
    op.create_table(
        "access_rules",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("days_of_week", sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_interval_minutes", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("min_party_size", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("max_party_size", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("max_covers_per_slot", sa.Integer(), nullable=True),
        sa.Column("advance_booking_days", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("cutoff_minutes", sa.Integer(), server_default=sa.text("120"), nullable=False),
        sa.Column("require_deposit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deposit_amount_cents", sa.Integer(), nullable=True),
        sa.Column("cancellation_policy_hours", sa.Integer(), nullable=True),
        sa.Column("cancellation_fee_cents", sa.Integer(), nullable=True),
        sa.Column("seating_areas", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
    )

    # --- reservations ---
    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("table_id", sa.Uuid(), nullable=True),
        sa.Column("access_rule_id", sa.Uuid(), nullable=True),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("status", sa.String(50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("special_requests", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["access_rule_id"], ["access_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reservation_venue_date", "reservations", ["venue_id", "date"])

    # --- waitlist_entries ---
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("estimated_wait_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), server_default=sa.text("'waiting'"), nullable=False),
        sa.Column("quoted_wait_minutes", sa.Integer(), nullable=True),
        sa.Column("check_in_time", sa.DateTime(), nullable=False),
        sa.Column("seated_time", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
    )

    # --- guest_visits ---
    op.create_table(
        "guest_visits",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("visited_at", sa.DateTime(), nullable=False),
        sa.Column("spend_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="SET NULL"),
    )

    # --- surveys ---
    op.create_table(
        "surveys",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("food_rating", sa.Integer(), nullable=True),
        sa.Column("service_rating", sa.Integer(), nullable=True),
        sa.Column("ambiance_rating", sa.Integer(), nullable=True),
        sa.Column("drinks_rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("surveys")
    op.drop_table("guest_visits")
    op.drop_table("waitlist_entries")
    op.drop_index("ix_reservation_venue_date", "reservations")
    op.drop_table("reservations")
    op.drop_table("access_rules")
    op.drop_table("tables")
    op.drop_table("floor_plans")
    op.drop_table("guest_tags")
    op.drop_table("guest_profiles")
    op.drop_table("tags")
    op.drop_table("venues")
    op.drop_table("users")
    op.drop_table("organizations")
