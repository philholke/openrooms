import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, Table, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

guest_tags = Table(
    "guest_tags",
    Base.metadata,
    Column("guest_id", ForeignKey("guest_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class GuestProfile(TimestampMixin, Base):
    __tablename__ = "guest_profiles"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_guest_org_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    birthday: Mapped[date | None] = mapped_column(nullable=True)
    anniversary: Mapped[date | None] = mapped_column(nullable=True)
    dietary_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="guest_profiles")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary=guest_tags,
        back_populates="guests",
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="guest")  # noqa: F821
    visits: Mapped[list["GuestVisit"]] = relationship(back_populates="guest")
    surveys: Mapped[list["Survey"]] = relationship(back_populates="guest")  # noqa: F821
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="guest")  # noqa: F821


class GuestVisit(TimestampMixin, Base):
    __tablename__ = "guest_visits"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"),
        nullable=True,
    )
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    spend_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    guest: Mapped["GuestProfile"] = relationship(back_populates="visits")
    venue: Mapped["Venue"] = relationship(back_populates="guest_visits")  # noqa: F821
    reservation: Mapped["Reservation | None"] = relationship(back_populates="guest_visits")  # noqa: F821
