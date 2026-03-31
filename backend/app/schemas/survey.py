import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SurveyCreate(BaseModel):
    venue_id: uuid.UUID
    guest_id: uuid.UUID
    reservation_id: uuid.UUID | None = None
    overall_rating: int = Field(..., ge=1, le=5)
    food_rating: int | None = Field(None, ge=1, le=5)
    service_rating: int | None = Field(None, ge=1, le=5)
    ambiance_rating: int | None = Field(None, ge=1, le=5)
    drinks_rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=5000)


class SurveyRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    guest_id: uuid.UUID
    reservation_id: uuid.UUID | None
    overall_rating: int
    food_rating: int | None
    service_rating: int | None
    ambiance_rating: int | None
    drinks_rating: int | None
    comment: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
