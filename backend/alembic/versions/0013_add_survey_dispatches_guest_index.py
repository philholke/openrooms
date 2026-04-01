"""add missing FK index on survey_dispatches.guest_id

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_survey_dispatches_guest_id", "survey_dispatches", ["guest_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_survey_dispatches_guest_id", table_name="survey_dispatches")
