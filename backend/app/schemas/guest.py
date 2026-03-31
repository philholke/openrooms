import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class GuestInfo(BaseModel):
    """Embedded in ReservationCreate / WaitlistEntryCreate — the minimal
    guest data captured during a booking or walk-in."""

    first_name: str = Field(..., max_length=255)
    last_name: str = Field(..., max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)


class GuestRead(BaseModel):
    """Read representation for nesting in reservation/waitlist responses."""

    id: uuid.UUID
    org_id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    birthday: date | None
    anniversary: date | None
    dietary_restrictions: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
