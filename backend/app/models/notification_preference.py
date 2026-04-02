import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class NotificationPreference(TimestampMixin, Base):
    """
    Per-venue toggle for each notification type.
    Defaults to enabled=True for all types.
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("venue_id", "notification_type", name="uq_notif_pref_venue_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # reservation_confirmed, reservation_reminder, survey_invite, cancellation_ack, pre_shift_report
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"),
    )

    venue: Mapped["Venue"] = relationship()  # noqa: F821
