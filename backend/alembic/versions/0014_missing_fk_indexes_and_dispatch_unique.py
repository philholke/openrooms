"""Add missing FK indexes on surveys, reservations, waitlist_entries
and unique constraint on survey_dispatches.reservation_id.

Revision ID: 0014
Revises: 0013
"""
from alembic import op

# revision identifiers
revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Missing FK indexes on surveys table
    op.create_index("ix_surveys_venue_id", "surveys", ["venue_id"])
    op.create_index("ix_surveys_guest_id", "surveys", ["guest_id"])
    op.create_index("ix_surveys_reservation_id", "surveys", ["reservation_id"])

    # Missing FK index on reservations.guest_id
    op.create_index("ix_reservations_guest_id", "reservations", ["guest_id"])

    # Missing FK index on waitlist_entries.venue_id
    op.create_index("ix_waitlist_entries_venue_id", "waitlist_entries", ["venue_id"])

    # Unique constraint to prevent duplicate dispatches per reservation
    op.create_index(
        "uq_survey_dispatches_reservation_id",
        "survey_dispatches",
        ["reservation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_survey_dispatches_reservation_id", table_name="survey_dispatches")
    op.drop_index("ix_waitlist_entries_venue_id", table_name="waitlist_entries")
    op.drop_index("ix_reservations_guest_id", table_name="reservations")
    op.drop_index("ix_surveys_reservation_id", table_name="surveys")
    op.drop_index("ix_surveys_guest_id", table_name="surveys")
    op.drop_index("ix_surveys_venue_id", table_name="surveys")
