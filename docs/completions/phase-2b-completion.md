# Phase 2B — Access Rules & Availability Engine: Completion Notes

**Date**: 2026-03-31
**Status**: Complete

---

## What Was Built

Phase 2B delivers access rule management and the availability engine — the core algorithm that turns scheduling rules + existing reservations into bookable time slots for guests.

---

## Task 2B.1 — Access Rule Pydantic Schemas

**File**: `backend/app/schemas/access_rule.py`

| Schema | Purpose |
|--------|---------|
| `AccessRuleCreate` | Request body for rule creation with cross-field validation |
| `AccessRuleUpdate` | Partial update (all fields optional), conditional validation |
| `AccessRuleRead` | Full response representation with `from_attributes` |

**Validations** (via `@model_validator(mode="after")`):
- `start_time < end_time`
- `min_party_size <= max_party_size`
- `days_of_week` values in 0–6, non-empty
- `slot_interval_minutes` in {15, 30, 45, 60}
- `start_date <= end_date` when both present
- `deposit_amount_cents` required if `require_deposit` is true

---

## Task 2B.2 — Access Rule Service Layer

**File**: `backend/app/services/access_rule.py`

| Function | Signature |
|----------|-----------|
| `create_access_rule` | `(db, venue_id, data) → AccessRule` |
| `list_access_rules` | `(db, venue_id, active_only=True) → list[AccessRule]` |
| `get_access_rule` | `(db, rule_id, venue_id) → AccessRule` (404 if not found) |
| `update_access_rule` | `(db, rule_id, venue_id, data) → AccessRule` |
| `deactivate_access_rule` | `(db, rule_id, venue_id) → AccessRule` (soft delete) |

All functions are fully async and accept `AsyncSession`.

---

## Task 2B.3 — Access Rule API Endpoints

**File**: `backend/app/api/v1/access_rules.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/access-rules` | manager+ | List rules for venue |
| POST | `/api/v1/venues/{venue_id}/access-rules` | manager+ | Create rule |
| PATCH | `/api/v1/access-rules/{rule_id}` | manager+ | Update rule |
| DELETE | `/api/v1/access-rules/{rule_id}` | manager+ | Soft-delete rule |

**Org-scoping**: PATCH/DELETE routes look up the rule first, then verify its venue belongs to the caller's org via `_get_venue_or_404`.

---

## Task 2B.4 — Availability Engine

**File**: `backend/app/services/availability.py`

The core function:
```python
async def get_available_slots(
    db, venue_id, target_date, party_size, *, venue_timezone="UTC"
) -> list[AvailableSlot]
```

**Algorithm**:
1. **Rule selection**: Query active `AccessRule` rows matching venue, weekday (`days_of_week.any(weekday)` → Postgres `ANY()`), date range, and party size range. Then filter by `advance_booking_days`.
2. **Slot generation**: For each rule, iterate from `start_time` to `end_time` at `slot_interval_minutes` steps. Apply cutoff filter for same-day bookings using venue-local time (`zoneinfo.ZoneInfo`).
3. **Batch cover count**: Single query grouping `SUM(party_size)` by `(time, access_rule_id)` over active reservations. Avoids N+1.
4. **Pacing filter**: Exclude slots where `booked_covers + party_size > max_covers_per_slot`.
5. **Sort**: Return slots ordered by time.

**Key design decisions**:
- Pacing counts **covers** (sum of party sizes), not reservation count. A slot with max 20 covers correctly handles mixed party sizes.
- Only 2 DB queries total regardless of slot count (rules + cover counts).
- Cutoff is timezone-aware via `zoneinfo.ZoneInfo` (stdlib, Python 3.9+). Falls back to UTC on error.
- `ACTIVE_STATUSES` constant defines which reservation statuses occupy capacity: `pending`, `confirmed`, `arrived`, `partially_arrived`, `seated`.

---

## Task 2B.5 — Availability API Endpoint

**File**: `backend/app/api/v1/availability.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/availability?date=YYYY-MM-DD&party_size=N` | **public** | Get available slots |

**Public endpoint** — no authentication required. Used by the booking widget. Validates venue exists and is active, passes venue timezone to the engine.

**Response schema** (`backend/app/schemas/availability.py`):
- `AvailableSlot`: `time`, `access_rule_id`, `access_rule_name`
- `AvailabilityResponse`: `venue_id`, `date`, `party_size`, `slots`

---

## File Summary

### New files

```
backend/app/schemas/access_rule.py    — AccessRule create/update/read schemas
backend/app/schemas/availability.py   — AvailableSlot + AvailabilityResponse schemas
backend/app/services/access_rule.py   — Access rule CRUD service
backend/app/services/availability.py  — Slot generation engine
backend/app/api/v1/access_rules.py    — Access rule REST endpoints
backend/app/api/v1/availability.py    — Public availability endpoint
```

### Modified files

```
backend/app/api/v1/router.py          — Added access_rules and availability sub-routers
```
