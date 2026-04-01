"""add missing indexes on guest_tags and server_assignments.user_id

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_guest_tags_guest_id", "guest_tags", ["guest_id"])
    op.create_index("ix_guest_tags_tag_id", "guest_tags", ["tag_id"])
    op.create_index("ix_server_assignments_user_id", "server_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_server_assignments_user_id", table_name="server_assignments")
    op.drop_index("ix_guest_tags_tag_id", table_name="guest_tags")
    op.drop_index("ix_guest_tags_guest_id", table_name="guest_tags")
