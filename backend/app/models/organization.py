import uuid

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        # Partial unique index: only active orgs must have unique slugs.
        # Soft-deleted orgs (is_active=False) no longer block slug reuse.
        # Mirrors the User.email partial index pattern from migration 0003/0005.
        Index(
            "ix_organizations_slug_active",
            "slug",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # Relationships
    venues: Mapped[list["Venue"]] = relationship(back_populates="organization")  # noqa: F821
    users: Mapped[list["User"]] = relationship(back_populates="organization")  # noqa: F821
    guest_profiles: Mapped[list["GuestProfile"]] = relationship(back_populates="organization")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(back_populates="organization")  # noqa: F821
