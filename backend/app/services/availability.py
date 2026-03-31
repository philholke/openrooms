"""
Availability engine — generates bookable time slots for a venue on a given date.

Algorithm:
  1. Load active AccessRules matching the target date, weekday, party size,
     and advance booking window.
  2. For each rule, generate time slots at the configured interval.
  3. For each slot, count existing active reservations (covers) against that
     rule's pacing limit.
  4. Exclude slots that are full or within the cutoff window.
  5. Return a flat, time-sorted list of available slots.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservation import AccessRule, Reservation
from app.models.venue import Venue
from app.schemas.availability import AvailableSlot

# Reservation statuses that count as "occupying" a slot.
ACTIVE_STATUSES = ["pending", "confirmed", "arrived", "partially_arrived", "seated"]


async def get_available_slots(
    db: AsyncSession,
    venue_id: uuid.UUID,
    target_date: date,
    party_size: int,
    *,
    venue_timezone: str = "UTC",
) -> list[AvailableSlot]:
    """Return all bookable slots for the given venue, date, and party size."""

    # ── 1. Load matching access rules ────────────────────────────────
    weekday = target_date.weekday()  # 0=Mon .. 6=Sun

    # Use the venue's timezone to determine "today", not the server's local tz.
    # A UTC server would otherwise be off by up to a day for western timezones,
    # causing incorrect advance booking window calculations.
    try:
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo(venue_timezone)).date()
    except (KeyError, Exception):
        today = date.today()

    days_until = (target_date - today).days

    stmt = (
        select(AccessRule)
        .where(
            AccessRule.venue_id == venue_id,
            AccessRule.is_active.is_(True),
            AccessRule.min_party_size <= party_size,
            AccessRule.max_party_size >= party_size,
            # The target weekday must be in the rule's days_of_week array.
            # Postgres: weekday = ANY(days_of_week)
            AccessRule.days_of_week.any(weekday),
        )
        .where(
            # Date range filters (NULLs mean unbounded)
            (AccessRule.start_date.is_(None)) | (AccessRule.start_date <= target_date),
            (AccessRule.end_date.is_(None)) | (AccessRule.end_date >= target_date),
        )
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()

    if not rules:
        return []

    # Filter by advance booking window
    rules = [r for r in rules if days_until <= r.advance_booking_days]

    if not rules:
        return []

    # ── 2. Generate candidate slots per rule ─────────────────────────
    # Pre-compute current time in the venue's timezone for cutoff checks.
    now_utc = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        venue_now = now_utc.astimezone(ZoneInfo(venue_timezone))
    except (KeyError, Exception) as exc:
        logger = logging.getLogger(__name__)
        logger.warning(
            "Invalid venue timezone '%s', falling back to UTC: %s",
            venue_timezone, exc,
        )
        venue_now = now_utc

    is_today = target_date == venue_now.date()

    # Collect (slot_time, rule) pairs
    candidates: list[tuple[time, AccessRule]] = []

    for rule in rules:
        slot = datetime.combine(target_date, rule.start_time)
        end = datetime.combine(target_date, rule.end_time)

        while slot < end:
            slot_time = slot.time()

            # Cutoff: if booking for today, exclude slots within cutoff_minutes of now
            if is_today:
                slot_dt = datetime.combine(target_date, slot_time)
                venue_now_naive = venue_now.replace(tzinfo=None)
                minutes_until_slot = (slot_dt - venue_now_naive).total_seconds() / 60
                if minutes_until_slot < rule.cutoff_minutes:
                    slot += timedelta(minutes=rule.slot_interval_minutes)
                    continue

            candidates.append((slot_time, rule))
            slot += timedelta(minutes=rule.slot_interval_minutes)

    if not candidates:
        return []

    # ── 3. Batch-load reservation counts per (time, access_rule_id) ──
    # Instead of N+1 queries, load all counts in one query.
    rule_ids = list({r.id for _, r in candidates})

    count_stmt = (
        select(
            Reservation.time,
            Reservation.access_rule_id,
            func.sum(Reservation.party_size).label("total_covers"),
        )
        .where(
            Reservation.venue_id == venue_id,
            Reservation.date == target_date,
            Reservation.access_rule_id.in_(rule_ids),
            Reservation.status.in_(ACTIVE_STATUSES),
        )
        .group_by(Reservation.time, Reservation.access_rule_id)
    )
    count_result = await db.execute(count_stmt)
    cover_counts: dict[tuple[time, uuid.UUID], int] = {
        (row.time, row.access_rule_id): row.total_covers
        for row in count_result.all()
    }

    # ── 4. Filter by pacing limits ───────────────────────────────────
    available: list[AvailableSlot] = []

    for slot_time, rule in candidates:
        if rule.max_covers_per_slot is not None:
            booked = cover_counts.get((slot_time, rule.id), 0)
            if booked + party_size > rule.max_covers_per_slot:
                continue

        available.append(
            AvailableSlot(
                time=slot_time,
                access_rule_id=rule.id,
                access_rule_name=rule.name,
            )
        )

    # ── 5. Sort by time and deduplicate ──────────────────────────────
    available.sort(key=lambda s: s.time)
    return available
