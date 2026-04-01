import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_tag_org_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_auto: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="tags")  # noqa: F821
    guests: Mapped[list["GuestProfile"]] = relationship(  # noqa: F821
        secondary="guest_tags",
        back_populates="tags",
    )
    auto_tag_rule: Mapped["AutoTagRule | None"] = relationship(back_populates="tag")  # noqa: F821
