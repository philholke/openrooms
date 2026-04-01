"""create survey_dispatches table for token-based public survey submission

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "survey_dispatches",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("guest_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("survey_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_survey_dispatches_token", "survey_dispatches", ["token"], unique=True)
    op.create_index("ix_survey_dispatches_venue_id", "survey_dispatches", ["venue_id"])
    op.create_index("ix_survey_dispatches_reservation_id", "survey_dispatches", ["reservation_id"])


def downgrade() -> None:
    op.drop_index("ix_survey_dispatches_reservation_id", table_name="survey_dispatches")
    op.drop_index("ix_survey_dispatches_venue_id", table_name="survey_dispatches")
    op.drop_index("ix_survey_dispatches_token", table_name="survey_dispatches")
    op.drop_table("survey_dispatches")
