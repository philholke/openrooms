import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, field_validator

from app.schemas.guest import GuestInfo, GuestRead

RESERVATION_STATUSES = Literal[
    "pending",
    "confirmed",
    "arrived",
    "partially_arrived",
    "seated",
    "completed",
    "no_show",
    "cancelled",
]


class ReservationCreate(BaseModel):
    """Guest-facing creation request (booking widget or staff-created)."""

    date: date
    time: time
    party_size: int
    access_rule_id: uuid.UUID
    guest: GuestInfo
    special_requests: str | None = None
    source: str | None = None  # widget, phone, walk_in, admin

    @field_validator("party_size")
    @classmethod
    def _party_size_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("party_size must be >= 1")
        return v


class ReservationUpdate(BaseModel):
    """Staff-facing update — mutable fields after creation."""

    table_id: uuid.UUID | None = None
    notes: str | None = None
    party_size: int | None = None
    special_requests: str | None = None

    @field_validator("party_size")
    @classmethod
    def _party_size_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("party_size must be >= 1")
        return v


class ReservationStatusUpdate(BaseModel):
    """Status-only update — enforced via the status machine."""

    status: RESERVATION_STATUSES


class ReservationCancel(BaseModel):
    reason: str | None = None


class ReservationRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    guest_id: uuid.UUID
    table_id: uuid.UUID | None
    access_rule_id: uuid.UUID | None
    party_size: int
    date: date
    time: time
    status: str
    source: str | None
    notes: str | None
    special_requests: str | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Nested read-only fields (populated by the service layer)
    guest: GuestRead | None = None
    table_label: str | None = None
    access_rule_name: str | None = None

    model_config = {"from_attributes": True}
