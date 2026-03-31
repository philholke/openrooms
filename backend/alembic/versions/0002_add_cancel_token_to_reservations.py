"""add cancel_token to reservations

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column("cancel_token", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_reservation_cancel_token", "reservations", ["cancel_token"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_reservation_cancel_token", "reservations", type_="unique")
    op.drop_column("reservations", "cancel_token")
