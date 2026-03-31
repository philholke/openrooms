import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrgUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, min_length=3, max_length=255, pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


class OrgRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
