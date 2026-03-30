import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class FloorPlan(TimestampMixin, Base):
    __tablename__ = "floor_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="floor_plans")  # noqa: F821
    tables: Mapped[list["Table"]] = relationship(back_populates="floor_plan")


class Table(TimestampMixin, Base):
    __tablename__ = "tables"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    floor_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("floor_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    min_capacity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    x_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    shape: Mapped[str] = mapped_column(
        String(50), default="rectangle", server_default=text("'rectangle'")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # Relationships
    floor_plan: Mapped["FloorPlan"] = relationship(back_populates="tables")
