import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.survey import SurveyRead
from app.schemas.tag import TagRead


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


# ─── CRUD schemas (Phase 4A) ─────────────────────────────────────────────


class GuestCreate(BaseModel):
    """Manual guest profile creation (phone-in guests, walk-ins, etc.)."""

    first_name: str = Field(..., max_length=255)
    last_name: str = Field(..., max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    birthday: date | None = None
    anniversary: date | None = None
    dietary_restrictions: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=5000)


class GuestUpdate(BaseModel):
    """Partial update — all fields optional."""

    first_name: str | None = Field(None, max_length=255)
    last_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    birthday: date | None = None
    anniversary: date | None = None
    dietary_restrictions: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=5000)


class GuestVisitRead(BaseModel):
    """Visit history entry with venue name denormalized."""

    id: uuid.UUID
    venue_id: uuid.UUID
    venue_name: str
    reservation_id: uuid.UUID | None
    visited_at: datetime
    spend_amount: Decimal | None
    notes: str | None

    model_config = {"from_attributes": True}


class GuestListRead(BaseModel):
    """Lightweight read for list/search views."""

    id: uuid.UUID
    org_id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    total_visits: int
    tag_names: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class GuestDetailRead(GuestRead):
    """Full profile with tags, visits, surveys, and aggregate stats."""

    tags: list[TagRead]
    visits: list[GuestVisitRead]
    surveys: list[SurveyRead]
    total_visits: int
    last_visit_date: datetime | None
    avg_overall_rating: float | None
