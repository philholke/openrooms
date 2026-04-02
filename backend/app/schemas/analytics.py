"""
Pydantic response schemas for analytics endpoints.
"""

from datetime import date

from pydantic import BaseModel, Field


# ─── Reservation Analytics ──────────────────────────────────────────────


class ReservationSummary(BaseModel):
    total_reservations: int
    total_covers: int
    avg_party_size: float
    cancellation_rate: float
    no_show_rate: float
    completion_rate: float
    avg_lead_time_days: float


class PeriodReservations(BaseModel):
    period: str
    reservations: int
    covers: int
    cancellations: int
    no_shows: int
    completions: int


class StatusBreakdown(BaseModel):
    completed: int = 0
    cancelled: int = 0
    no_show: int = 0
    confirmed: int = 0
    pending: int = 0
    seated: int = 0
    arrived: int = 0


class SourceBreakdown(BaseModel):
    source: str
    count: int


class DayOfWeekStats(BaseModel):
    day: int
    label: str
    reservations: int
    covers: int


class HourStats(BaseModel):
    hour: int
    reservations: int
    covers: int


class ReservationAnalytics(BaseModel):
    summary: ReservationSummary
    by_period: list[PeriodReservations]
    by_status: StatusBreakdown
    by_source: list[SourceBreakdown]
    by_day_of_week: list[DayOfWeekStats]
    peak_hours: list[HourStats]


# ─── Guest Analytics ────────────────────────────────────────────────────


class GuestSummary(BaseModel):
    total_guests: int
    new_guests_in_period: int
    returning_guests_in_period: int
    return_rate: float
    avg_visits_per_guest: float


class GuestGrowth(BaseModel):
    period: str
    new_guests: int
    cumulative: int


class TopGuest(BaseModel):
    id: str
    name: str
    visits: int
    last_visit: str | None


class TagDistribution(BaseModel):
    tag_id: str
    tag_name: str
    count: int
    color: str | None


class GuestAnalytics(BaseModel):
    summary: GuestSummary
    growth: list[GuestGrowth]
    top_guests: list[TopGuest]
    tag_distribution: list[TagDistribution]


# ─── Operations Analytics ───────────────────────────────────────────────


class OperationsSummary(BaseModel):
    avg_turn_time_minutes: float | None
    table_utilization_rate: float | None
    walk_in_ratio: float
    waitlist_conversion_rate: float
    waitlist_abandonment_rate: float


class SectionUtilization(BaseModel):
    section: str
    covers: int
    reservation_count: int


class TurnTimeByPartySize(BaseModel):
    party_size: int
    avg_turn_time_minutes: float


class WaitlistStats(BaseModel):
    total_entries: int
    seated: int
    cancelled: int
    no_show: int
    avg_wait_minutes: float | None


class OperationsAnalytics(BaseModel):
    summary: OperationsSummary
    utilization_by_section: list[SectionUtilization]
    turn_time_by_party_size: list[TurnTimeByPartySize]
    waitlist_stats: WaitlistStats


# ─── Query Parameters ───────────────────────────────────────────────────


class AnalyticsQuery(BaseModel):
    date_from: date
    date_to: date
    granularity: str = "day"  # day, week, month

    model_config = {"extra": "forbid"}
