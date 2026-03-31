import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VenueCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    address: str | None = Field(None, max_length=500)
    timezone: str = Field("UTC", max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


class VenueUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    timezone: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


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
