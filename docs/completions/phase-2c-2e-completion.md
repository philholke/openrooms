# Phase 2C + 2E — Reservations & Guest Auto-Creation: Completion Notes

**Date**: 2026-03-31
**Status**: Complete

---

## What Was Built

Phase 2E delivers the guest profile upsert (the bridge between bookings and CRM). Phase 2C delivers the full reservation lifecycle: creation with availability validation, CRUD, the status machine with enforced transitions, and side-effect triggers.

---

## Task 2E.1 — Guest Upsert Service

**File**: `backend/app/services/guest.py`

| Function | Signature |
|----------|-----------|
| `get_or_create_guest` | `(db, org_id, first_name, last_name, email?, phone?) → GuestProfile` |

**Logic**:
1. If `email` provided → look up by `(org_id, email)`
   - Found → enrich (fill NULLs, never overwrite existing data) → return
   - Not found → create new profile
2. No email → always create new profile (phone-based dedup is future scope)

**Design decision**: "Enrich, don't overwrite" prevents staff corrections from being reverted by subsequent bookings. If a manager renames "Mike" to "Michael", a new booking as "Mike" won't revert it.

---

## Task 2E.2 — Guest Schemas

**File**: `backend/app/schemas/guest.py`

| Schema | Purpose |
|--------|---------|
| `GuestInfo` | Embedded in `ReservationCreate` and future `WaitlistEntryCreate` — minimal booking-time data |
| `GuestRead` | Full read representation for nesting in reservation/waitlist responses |

`GuestInfo.email` uses `EmailStr | None` — optional for walk-ins (phone only), required for widget bookings (enforced at the form level, not schema level, since the schema serves both flows).

---

## Task 2C.1 — Reservation Pydantic Schemas

**File**: `backend/app/schemas/reservation.py`

| Schema | Purpose |
|--------|---------|
| `ReservationCreate` | Guest-facing: date, time, party_size, access_rule_id, guest (GuestInfo), special_requests, source |
| `ReservationUpdate` | Staff-facing: table_id, notes, party_size, special_requests |
| `ReservationStatusUpdate` | Status only — uses `Literal` for valid status values |
| `ReservationCancel` | Optional reason field |
| `ReservationRead` | Full representation + nested `guest` (GuestRead), `table_label`, `access_rule_name` |

`ReservationRead` includes nested fields populated by the service layer from eagerly loaded relationships, not by Pydantic's `from_attributes` alone.

---

## Task 2C.2 + 2C.3 — Reservation Service & Status Machine

**File**: `backend/app/services/reservation.py`

### Status Machine

Defined as a constant dict:

```
pending       → {confirmed, cancelled}
confirmed     → {arrived, partially_arrived, cancelled, no_show}
arrived       → {seated, cancelled, no_show}
partially_arrived → {seated, cancelled, no_show}
seated        → {completed}
completed     → ∅ (terminal)
no_show       → ∅ (terminal)
cancelled     → ∅ (terminal)
```

`validate_transition(current, target)` raises HTTP 409 on invalid transitions with a clear error message listing allowed targets.

### Side Effects

| Transition | Side Effect |
|------------|-------------|
| → `completed` | Auto-creates `GuestVisit` record (guest_id, venue_id, reservation_id, visited_at) |
| → `cancelled` | Sets `cancelled_at = utcnow()` |
| → `cancelled` (via cancel endpoint) | Also appends `[Cancelled] reason` to notes |

### Service Functions

| Function | Purpose |
|----------|---------|
| `create_reservation(db, venue_id, org_id, data, venue_timezone)` | Validates slot availability, upserts guest, sets initial status (confirmed or pending if deposit required) |
| `list_reservations(db, venue_id, date?, statuses?, search?, page, per_page)` | Paginated list with date/status/name filters, eager-loaded relationships |
| `get_reservation(db, reservation_id, venue_id)` | Single reservation with relationships |
| `update_reservation(db, reservation_id, venue_id, data)` | Update mutable fields (table, notes, party size, special requests) |
| `update_status(db, reservation_id, venue_id, new_status)` | Status machine transition with side effects |
| `cancel_reservation(db, reservation_id, venue_id, reason?)` | Convenience wrapper — transitions to cancelled with optional reason |

**Availability re-validation on create**: Even though the frontend checked availability, `create_reservation` calls `get_available_slots` again to prevent race conditions.

**Eager loading**: `_base_query()` uses `joinedload` for guest, table, and access_rule on all read paths. `_to_read()` converts ORM → Pydantic with nested fields populated.

---

## Task 2C.4 — Reservation API Endpoints

**File**: `backend/app/api/v1/reservations.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/reservations` | staff+ | List with date/status/search filters, paginated |
| POST | `/api/v1/venues/{venue_id}/reservations` | **public** | Create reservation (widget + staff) |
| GET | `/api/v1/reservations/{id}` | staff+ | Get single reservation |
| PATCH | `/api/v1/reservations/{id}` | staff+ | Update fields (table, notes, party size) |
| PATCH | `/api/v1/reservations/{id}/status` | staff+ | Advance status (uses status machine) |
| POST | `/api/v1/reservations/{id}/cancel` | **public** | Cancel reservation (widget + staff) |

**Public endpoints**: Create and cancel are unauthenticated — guests use these from the booking widget and confirmation email. Staff endpoints require auth.

**List filters**:
- `date` (YYYY-MM-DD)
- `status` (comma-separated: `?status=confirmed,arrived`)
- `search` (matches guest first/last name via `ILIKE`)

---

## File Summary

### New files

```
backend/app/services/guest.py         — Guest profile upsert (get_or_create_guest)
backend/app/services/reservation.py   — Reservation CRUD + status machine + side effects
backend/app/schemas/guest.py          — GuestInfo + GuestRead schemas
backend/app/schemas/reservation.py    — Reservation create/update/status/cancel/read schemas
backend/app/api/v1/reservations.py    — Reservation REST endpoints
```

### Modified files

```
backend/app/api/v1/router.py          — Added reservations sub-router
```
