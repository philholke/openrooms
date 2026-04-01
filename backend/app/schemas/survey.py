import uuid
from datetime import date, datetime

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


# ─── Public survey schemas (Phase 4D) ────────────────────────────────────


class SurveyPublicInfo(BaseModel):
    """Returned by GET /public/surveys/{token} — enough to render the form."""

    venue_name: str
    guest_first_name: str
    reservation_date: date


class SurveyPublicSubmit(BaseModel):
    """Guest-submitted survey via public token link."""

    overall_rating: int = Field(..., ge=1, le=5)
    food_rating: int | None = Field(None, ge=1, le=5)
    service_rating: int | None = Field(None, ge=1, le=5)
    ambiance_rating: int | None = Field(None, ge=1, le=5)
    drinks_rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=5000)


class RatingDistribution(BaseModel):
    """Count of surveys per rating bucket (1-5)."""

    rating: int
    count: int


class SurveyStats(BaseModel):
    """Aggregated survey statistics for a venue."""

    total_responses: int
    avg_overall: float | None
    avg_food: float | None
    avg_service: float | None
    avg_ambiance: float | None
    avg_drinks: float | None
    distribution: list[RatingDistribution]
