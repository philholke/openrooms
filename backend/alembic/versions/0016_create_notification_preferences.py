"""Create notification_preferences table.

Revision ID: 0016
Revises: 0015
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("venue_id", sa.Uuid(), sa.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "notification_type", name="uq_notif_pref_venue_type"),
    )
    op.create_index("ix_notification_preferences_venue_id", "notification_preferences", ["venue_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_preferences_venue_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
