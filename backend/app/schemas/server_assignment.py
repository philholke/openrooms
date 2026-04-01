import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ServerAssignmentCreate(BaseModel):
    date: date
    section: str = Field(..., max_length=100)
    user_id: uuid.UUID


class ServerAssignmentRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    date: date
    section: str
    user_id: uuid.UUID
    user_name: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
