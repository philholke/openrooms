import uuid

from sqlalchemy import Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AutoTagRule(TimestampMixin, Base):
    __tablename__ = "auto_tag_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"),
    )

    # Relationships
    tag: Mapped["Tag"] = relationship(back_populates="auto_tag_rule")  # noqa: F821
    organization: Mapped["Organization"] = relationship(back_populates="auto_tag_rules")  # noqa: F821
