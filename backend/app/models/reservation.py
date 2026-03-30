import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AccessRule(TimestampMixin, Base):
    __tablename__ = "access_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    days_of_week: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=30, server_default=text("30")
    )
    min_party_size: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1")
    )
    max_party_size: Mapped[int] = mapped_column(
        Integer, default=20, server_default=text("20")
    )
    max_covers_per_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advance_booking_days: Mapped[int] = mapped_column(
        Integer, default=30, server_default=text("30")
    )
    cutoff_minutes: Mapped[int] = mapped_column(
        Integer, default=120, server_default=text("120")
    )
    require_deposit: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    deposit_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancellation_policy_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancellation_fee_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seating_areas: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="access_rules")  # noqa: F821
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="access_rule")


class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_reservation_venue_date", "venue_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tables.id", ondelete="SET NULL"),
        nullable=True,
    )
    access_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("access_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
    )  # pending, confirmed, arrived, partially_arrived, seated, completed, no_show, cancelled
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # widget, phone, walk_in, admin
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="reservations")  # noqa: F821
    guest: Mapped["GuestProfile"] = relationship(back_populates="reservations")  # noqa: F821
    table: Mapped["Table | None"] = relationship()  # noqa: F821
    access_rule: Mapped["AccessRule | None"] = relationship(back_populates="reservations")
    surveys: Mapped[list["Survey"]] = relationship(back_populates="reservation")  # noqa: F821


class WaitlistEntry(TimestampMixin, Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_wait_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="waiting",
        server_default=text("'waiting'"),
        nullable=False,
    )  # waiting, notified, seated, cancelled, no_show
    quoted_wait_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_in_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    seated_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="waitlist_entries")  # noqa: F821
    guest: Mapped["GuestProfile"] = relationship()  # noqa: F821
