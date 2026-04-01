import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AutoTagConditions(BaseModel):
    """
    Conditions are AND-combined. Each field is optional — omitted = no filter.
    At least one condition must be specified.
    """

    visit_count_gte: int | None = Field(None, ge=1, description="Total visits >= N")
    visit_count_lte: int | None = Field(None, ge=0, description="Total visits <= N")
    last_visit_within_days: int | None = Field(None, ge=1, description="Visited within last N days")
    last_visit_not_within_days: int | None = Field(None, ge=1, description="NOT visited in last N days")
    total_spend_gte: int | None = Field(None, ge=0, description="Lifetime spend (cents) >= N")
    avg_rating_gte: float | None = Field(None, ge=1.0, le=5.0, description="Avg survey rating >= N")
    avg_rating_lte: float | None = Field(None, ge=1.0, le=5.0, description="Avg survey rating <= N")
    has_tag: str | None = Field(None, max_length=255, description="Must have tag with this name")
    not_has_tag: str | None = Field(None, max_length=255, description="Must NOT have tag with this name")
    venue_id: uuid.UUID | None = Field(None, description="Scope visits to specific venue")

    @model_validator(mode="after")
    def _at_least_one_condition(self) -> "AutoTagConditions":
        if not any(
            v is not None
            for v in self.model_dump().values()
        ):
            raise ValueError("At least one condition must be specified")
        return self


class AutoTagRuleCreate(BaseModel):
    """Create or replace the auto-tag rule for a tag."""

    conditions: AutoTagConditions


class AutoTagRuleRead(BaseModel):
    id: uuid.UUID
    tag_id: uuid.UUID
    org_id: uuid.UUID
    conditions: AutoTagConditions
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkEvaluateResult(BaseModel):
    """Response from bulk auto-tag evaluation."""

    guests_evaluated: int
    tags_applied: int
    tags_removed: int
