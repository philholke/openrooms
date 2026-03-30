import uuid

from sqlalchemy import ForeignKey, Integer, Text, text
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
        nullable=False,
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"),
        nullable=True,
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guest_profiles.id", ondelete="CASCADE"),
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
