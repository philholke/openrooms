import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ServerAssignment(TimestampMixin, Base):
    __tablename__ = "server_assignments"
    __table_args__ = (
        UniqueConstraint(
            "venue_id", "date", "section",
            name="uq_server_assignment_venue_date_section",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"),
    )

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="server_assignments")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="server_assignments")  # noqa: F821
