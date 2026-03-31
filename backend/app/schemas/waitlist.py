import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.guest import GuestInfo, GuestRead

WAITLIST_STATUSES = Literal["waiting", "notified", "seated", "cancelled", "no_show"]


class WaitlistEntryCreate(BaseModel):
    party_size: int
    guest: GuestInfo
    quoted_wait_minutes: int | None = Field(None, ge=0, le=480)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("party_size")
    @classmethod
    def _party_size_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("party_size must be >= 1")
        return v


class WaitlistEntryUpdate(BaseModel):
    status: WAITLIST_STATUSES | None = None
    notes: str | None = Field(None, max_length=2000)
    quoted_wait_minutes: int | None = Field(None, ge=0, le=480)


class WaitlistEntryRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    guest_id: uuid.UUID
    party_size: int
    estimated_wait_minutes: int | None
    status: str
    quoted_wait_minutes: int | None
    check_in_time: datetime
    seated_time: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Nested
    guest: GuestRead | None = None

    model_config = {"from_attributes": True}
