# Phase 2D — Waitlist CRUD: Completion Notes

**Date**: 2026-03-31
**Status**: Complete

---

## What Was Built

Phase 2D delivers the waitlist system — host stand staff can add walk-in guests, manage their queue position, and seat them (optionally creating a linked reservation for tracking).

---

## Task 2D.1 — Waitlist Pydantic Schemas

**File**: `backend/app/schemas/waitlist.py`

| Schema | Purpose |
|--------|---------|
| `WaitlistEntryCreate` | `party_size`, `guest` (GuestInfo), `quoted_wait_minutes`, `notes` |
| `WaitlistEntryUpdate` | `status`, `notes`, `quoted_wait_minutes` — all optional |
| `WaitlistEntryRead` | Full representation with nested `guest` (GuestRead) |

Reuses `GuestInfo` from guest schemas for consistency with the reservation create flow.

---

## Task 2D.2 — Waitlist Service Layer

**File**: `backend/app/services/waitlist.py`

### Status Machine

```
waiting   → {notified, seated, cancelled, no_show}
notified  → {seated, cancelled, no_show}
seated    → ∅ (terminal)
cancelled → ∅ (terminal)
no_show   → ∅ (terminal)
```

Simpler than the reservation machine — no deposit/confirmation flow needed for walk-ins.

### Service Functions

| Function | Purpose |
|----------|---------|
| `add_to_waitlist(db, venue_id, org_id, data)` | Creates guest profile (via upsert), sets `check_in_time=now`, status `waiting` |
| `list_waitlist(db, venue_id, active_only=True)` | FIFO-ordered list; `active_only` filters to `waiting`+`notified` |
| `update_waitlist_entry(db, entry_id, venue_id, data)` | Status transitions with validation, auto-sets `seated_time` on seat |
| `seat_from_waitlist(db, entry_id, venue_id, table_id?)` | Seats guest + optionally creates walk-in `Reservation(source="walk_in", status="seated")` |

### Key Details

- **Guest upsert**: `add_to_waitlist` calls `get_or_create_guest()` — walk-ins get CRM profiles just like online bookings.
- **Walk-in → Reservation bridge**: `seat_from_waitlist` with a `table_id` creates a Reservation with `source="walk_in"`. Walk-ins appear on the same reservation list/timeline as bookings — revenue and visit tracking are uniform.
- **FIFO ordering**: List always sorts by `check_in_time ASC`. Host sees longest-waiting guest first.
- **`seated_time` side effect**: Automatically recorded on transition to `seated`, enabling wait-time analytics.

---

## Task 2D.3 — Waitlist API Endpoints

**File**: `backend/app/api/v1/waitlist.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/waitlist` | staff+ | List active (or all) waitlist entries |
| POST | `/api/v1/venues/{venue_id}/waitlist` | staff+ | Add guest to waitlist |
| PATCH | `/api/v1/waitlist/{entry_id}` | staff+ | Update entry (status, notes, quoted wait) |

All endpoints are staff-only (unlike reservations which have public create/cancel). Walk-ins are managed at the host stand, not self-service.

**Org-scoping**: PATCH route looks up the entry's `venue_id`, then verifies the venue belongs to the caller's org.

---

## File Summary

### New files

```
backend/app/schemas/waitlist.py       — Waitlist create/update/read schemas
backend/app/services/waitlist.py      — Waitlist CRUD + status machine + seat-from-waitlist
backend/app/api/v1/waitlist.py        — Waitlist REST endpoints
```

### Modified files

```
backend/app/api/v1/router.py          — Added waitlist sub-router
```
