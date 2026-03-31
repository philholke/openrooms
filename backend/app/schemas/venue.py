import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator


def _validate_iana_timezone(v: str) -> str:
    """Validate that the string is a known IANA timezone identifier."""
    try:
        ZoneInfo(v)
    except (KeyError, Exception):
        raise ValueError(
            f"Invalid timezone '{v}'. Must be a valid IANA timezone "
            f"(e.g. 'America/New_York', 'Europe/London', 'UTC')."
        )
    return v


class VenueCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., min_length=3, max_length=255, pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
    address: str | None = Field(None, max_length=500)
    timezone: str = Field("UTC", max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, v: str) -> str:
        return _validate_iana_timezone(v)


class VenueUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, min_length=3, max_length=255, pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
    address: str | None = Field(None, max_length=500)
    timezone: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_iana_timezone(v)
        return v


class VenueRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    slug: str
    address: str | None
    timezone: str
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
