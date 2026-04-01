import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.guest import GuestInfo, GuestRead

WAITLIST_STATUSES = Literal["waiting", "notified", "seated", "cancelled", "no_show"]


class WaitlistEntryCreate(BaseModel):
    party_size: int = Field(..., ge=1, le=100)
    guest: GuestInfo
    quoted_wait_minutes: int | None = Field(None, ge=0, le=480)
    notes: str | None = Field(None, max_length=2000)


class WaitlistEntryUpdate(BaseModel):
    status: WAITLIST_STATUSES | None = None
    notes: str | None = Field(None, max_length=2000)
    quoted_wait_minutes: int | None = Field(None, ge=0, le=480)


class WaitlistSeatRequest(BaseModel):
    table_id: uuid.UUID | None = None


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
