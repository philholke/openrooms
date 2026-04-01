import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Survey(TimestampMixin, Base):
    __tablename__ = "surveys"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    food_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    service_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    ambiance_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    drinks_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="surveys")  # noqa: F821
    reservation: Mapped["Reservation | None"] = relationship(back_populates="surveys")  # noqa: F821
    guest: Mapped["GuestProfile"] = relationship(back_populates="surveys")  # noqa: F821
    dispatch: Mapped["SurveyDispatch | None"] = relationship(back_populates="survey")


class SurveyDispatch(TimestampMixin, Base):
    """
    Token-based survey invitation created when a reservation completes.
    Guests use the token to submit feedback without authentication.
    """

    __tablename__ = "survey_dispatches"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    survey_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("surveys.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    venue: Mapped["Venue"] = relationship()  # noqa: F821
    reservation: Mapped["Reservation"] = relationship()  # noqa: F821
    guest: Mapped["GuestProfile"] = relationship()  # noqa: F821
    survey: Mapped["Survey | None"] = relationship(back_populates="dispatch")
