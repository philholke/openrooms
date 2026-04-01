import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Venue(TimestampMixin, Base):
    __tablename__ = "venues"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_venue_org_slug"),
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
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", server_default=text("'UTC'"))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="venues")  # noqa: F821
    floor_plans: Mapped[list["FloorPlan"]] = relationship(back_populates="venue")  # noqa: F821
    access_rules: Mapped[list["AccessRule"]] = relationship(back_populates="venue")  # noqa: F821
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="venue")  # noqa: F821
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="venue")  # noqa: F821
    surveys: Mapped[list["Survey"]] = relationship(back_populates="venue")  # noqa: F821
    guest_visits: Mapped[list["GuestVisit"]] = relationship(back_populates="venue")  # noqa: F821
    server_assignments: Mapped[list["ServerAssignment"]] = relationship(back_populates="venue")  # noqa: F821
