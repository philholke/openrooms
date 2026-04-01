import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Shared validation helpers ───────────────────────────────────────────

def _validate_seating_areas_items(v: list[str] | None) -> list[str] | None:
    """Validate individual seating area names (shared by Create and Update)."""
    if v is not None:
        for area in v:
            if len(area) > 100:
                raise ValueError("Each seating area name must be at most 100 characters")
    return v


def _validate_access_rule_pairs(
    *,
    start_time: time | None,
    end_time: time | None,
    min_party_size: int | None,
    max_party_size: int | None,
    days_of_week: list[int] | None,
    slot_interval_minutes: int | None,
    start_date: date | None,
    end_date: date | None,
    require_deposit: bool | None,
    deposit_amount_cents: int | None,
) -> None:
    """Cross-field validation shared between Create and Update schemas.
    For Update, fields may be None (not provided) — only validate when both
    fields in a pair are present."""
    if start_time is not None and end_time is not None:
        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")
    if min_party_size is not None and max_party_size is not None:
        if min_party_size > max_party_size:
            raise ValueError("min_party_size must be <= max_party_size")
    if days_of_week is not None:
        if not days_of_week:
            raise ValueError("days_of_week must not be empty")
        if not all(0 <= d <= 6 for d in days_of_week):
            raise ValueError("days_of_week values must be 0-6 (Mon-Sun)")
    if slot_interval_minutes is not None:
        if slot_interval_minutes not in {15, 30, 45, 60}:
            raise ValueError("slot_interval_minutes must be 15, 30, 45, or 60")
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")
    if require_deposit and not deposit_amount_cents:
        raise ValueError("deposit_amount_cents is required when require_deposit is true")


# ── Schemas ─────────────────────────────────────────────────────────────

class AccessRuleCreate(BaseModel):
    name: str = Field(..., max_length=255)
    days_of_week: list[int]
    start_date: date | None = None
    end_date: date | None = None
    start_time: time
    end_time: time
    slot_interval_minutes: int = 30
    min_party_size: int = Field(1, ge=1, le=100)
    max_party_size: int = Field(20, ge=1, le=100)
    max_covers_per_slot: int | None = Field(None, ge=1)
    advance_booking_days: int = Field(30, ge=1, le=365)
    cutoff_minutes: int = Field(120, ge=0, le=1440)
    require_deposit: bool = False
    deposit_amount_cents: int | None = Field(None, ge=0)
    cancellation_policy_hours: int | None = Field(None, ge=0)
    cancellation_fee_cents: int | None = Field(None, ge=0)
    seating_areas: list[str] | None = Field(None, max_length=20)

    @field_validator("seating_areas")
    @classmethod
    def _check_seating_areas(cls, v: list[str] | None) -> list[str] | None:
        return _validate_seating_areas_items(v)

    @model_validator(mode="after")
    def _validate(self):
        _validate_access_rule_pairs(
            start_time=self.start_time,
            end_time=self.end_time,
            min_party_size=self.min_party_size,
            max_party_size=self.max_party_size,
            days_of_week=self.days_of_week,
            slot_interval_minutes=self.slot_interval_minutes,
            start_date=self.start_date,
            end_date=self.end_date,
            require_deposit=self.require_deposit,
            deposit_amount_cents=self.deposit_amount_cents,
        )
        return self


class AccessRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    days_of_week: list[int] | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    slot_interval_minutes: int | None = None
    min_party_size: int | None = None
    max_party_size: int | None = None
    max_covers_per_slot: int | None = None
    advance_booking_days: int | None = None
    cutoff_minutes: int | None = None
    require_deposit: bool | None = None
    deposit_amount_cents: int | None = None
    cancellation_policy_hours: int | None = None
    cancellation_fee_cents: int | None = None
    seating_areas: list[str] | None = Field(None, max_length=20)

    @field_validator("seating_areas")
    @classmethod
    def _check_seating_areas(cls, v: list[str] | None) -> list[str] | None:
        return _validate_seating_areas_items(v)

    @model_validator(mode="after")
    def _validate(self):
        # When both fields in a pair are provided, validate them against each other.
        # Single-field updates are validated in the service layer against DB values.
        _validate_access_rule_pairs(
            start_time=self.start_time,
            end_time=self.end_time,
            min_party_size=self.min_party_size,
            max_party_size=self.max_party_size,
            days_of_week=self.days_of_week,
            slot_interval_minutes=self.slot_interval_minutes,
            start_date=self.start_date,
            end_date=self.end_date,
            require_deposit=self.require_deposit,
            deposit_amount_cents=self.deposit_amount_cents,
        )
        return self


class AccessRuleRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    name: str
    days_of_week: list[int]
    start_date: date | None
    end_date: date | None
    start_time: time
    end_time: time
    slot_interval_minutes: int
    min_party_size: int
    max_party_size: int
    max_covers_per_slot: int | None
    advance_booking_days: int
    cutoff_minutes: int
    require_deposit: bool
    deposit_amount_cents: int | None
    cancellation_policy_hours: int | None
    cancellation_fee_cents: int | None
    seating_areas: list[str] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
