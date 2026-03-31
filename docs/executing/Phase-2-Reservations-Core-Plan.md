# Phase 2: Reservations Core — Implementation Plan

**Goal**: Working reservation flow from availability check to completion. A guest can book through the widget. Staff can manage reservations, advance statuses, and manage the waitlist.

**Prerequisite**: Phase 1 (Foundation) must be complete — auth, org/venue/user CRUD, API envelope, and seed data all functional.

---

## Table of Contents

1. [Phase 2A — Backend Foundation](#phase-2a--backend-foundation)
2. [Phase 2B — Access Rules & Availability Engine](#phase-2b--access-rules--availability-engine)
3. [Phase 2C — Reservation CRUD & Status Machine](#phase-2c--reservation-crud--status-machine)
4. [Phase 2D — Waitlist CRUD](#phase-2d--waitlist-crud)
5. [Phase 2E — Guest Profile Auto-Creation](#phase-2e--guest-profile-auto-creation)
6. [Phase 2F — Staff Reservation View (Frontend)](#phase-2f--staff-reservation-view-frontend)
7. [Phase 2G — Booking Widget (Frontend)](#phase-2g--booking-widget-frontend)
8. [Exit Criteria](#exit-criteria)

---

## Phase 2A — Backend Foundation

**Goal**: Shared infrastructure that all Phase 2 endpoints depend on — the API envelope, auth middleware, and Pydantic schema patterns.

> This section is a prerequisite gate. If Phase 1 delivered these items, mark them done and move on.

### Task 2A.1 — API Response Envelope

Create a reusable response wrapper so every endpoint returns the standard format.

**File**: `backend/app/schemas/envelope.py`

```python
{
  "data": T | list[T],
  "meta": { "page": int, "per_page": int, "total": int } | null,
  "errors": list[ErrorDetail] | null
}
```

- Generic `Envelope[T]` and `PaginatedEnvelope[T]` Pydantic models.
- `ErrorDetail` schema with `field`, `message`, `code`.
- Helper functions: `ok(data)`, `paginated(data, page, per_page, total)`, `error(errors, status_code)`.

### Task 2A.2 — Auth & JWT Middleware

Implement JWT-based authentication required for staff endpoints.

**Files**:
- `backend/app/core/security.py` — `create_access_token()`, `create_refresh_token()`, `verify_token()`, password hashing with `passlib[bcrypt]`.
- `backend/app/core/dependencies.py` — `get_current_user` dependency (extracts JWT from `Authorization: Bearer` header, loads User from DB). Also `get_current_org` (derives org from user). Role-check dependencies: `require_role(min_role)`.

**Endpoints** (in `backend/app/api/v1/auth.py`):
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create org + owner user. Returns JWT pair |
| POST | `/api/v1/auth/login` | Email + password → JWT pair |
| POST | `/api/v1/auth/refresh` | Refresh token → new access token |

### Task 2A.3 — Org, Venue, and User CRUD

Basic CRUD endpoints with role-based guards. These are needed to create the venue context that reservations live under.

**Files**:
- `backend/app/api/v1/organizations.py` — GET/PATCH current org
- `backend/app/api/v1/venues.py` — full CRUD scoped to current org
- `backend/app/api/v1/users.py` — full CRUD scoped to current org
- Corresponding schemas in `backend/app/schemas/organization.py`, `venue.py`, `user.py`

### Task 2A.4 — Alembic Initial Migration

Generate and apply the initial migration from all existing models.

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Verify all 12 tables are created with correct constraints, indexes, and defaults.

### Task 2A.5 — Seed Data Script

**File**: `backend/scripts/seed.py`

Creates a demo dataset for development:
- 1 Organization ("Demo Restaurant Group", slug: `demo`)
- 1 Owner user (email: `owner@demo.com`, password: `password`)
- 2 Venues ("Downtown Bistro" + "Waterfront Grill") with realistic timezones
- 1 FloorPlan per venue with 8-12 tables each (varied capacities, sections)
- 3-4 AccessRules per venue (lunch, dinner, brunch-weekend)
- 5-10 GuestProfiles with varied data

---

## Phase 2B — Access Rules & Availability Engine

**Goal**: Staff can create access rules. The availability API returns bookable time slots.

### Task 2B.1 — Access Rule Pydantic Schemas

**File**: `backend/app/schemas/access_rule.py`

| Schema | Purpose |
|--------|---------|
| `AccessRuleCreate` | Request body for creating a rule |
| `AccessRuleUpdate` | Partial update (all fields optional) |
| `AccessRuleRead` | Response representation |

Key validations:
- `start_time < end_time`
- `min_party_size <= max_party_size`
- `days_of_week` values in range 0-6
- `slot_interval_minutes` in {15, 30, 45, 60}
- `deposit_amount_cents` required if `require_deposit` is true
- `start_date <= end_date` when both present

### Task 2B.2 — Access Rule Service Layer

**File**: `backend/app/services/access_rule.py`

Functions:
- `create_access_rule(db, venue_id, data) → AccessRule`
- `list_access_rules(db, venue_id, active_only=True) → list[AccessRule]`
- `get_access_rule(db, rule_id) → AccessRule`
- `update_access_rule(db, rule_id, data) → AccessRule`
- `deactivate_access_rule(db, rule_id) → AccessRule` (soft delete)

All functions accept an `AsyncSession` and are fully async.

### Task 2B.3 — Access Rule API Endpoints

**File**: `backend/app/api/v1/access_rules.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/venues/{venue_id}/access-rules` | manager+ | List rules for venue |
| POST | `/venues/{venue_id}/access-rules` | manager+ | Create rule |
| PATCH | `/access-rules/{id}` | manager+ | Update rule |
| DELETE | `/access-rules/{id}` | manager+ | Soft-delete rule |

Register sub-router in `backend/app/api/v1/router.py`.

### Task 2B.4 — Availability Engine (Core Algorithm)

**File**: `backend/app/services/availability.py`

This is the most critical piece of Phase 2. Implements the slot generation algorithm:

```
get_available_slots(db, venue_id, date, party_size) → list[AvailableSlot]
```

**Algorithm**:
1. Load all active AccessRules for the venue where:
   - `days_of_week` includes the target weekday
   - `start_date` is null OR `start_date <= date`
   - `end_date` is null OR `end_date >= date`
   - `min_party_size <= party_size <= max_party_size`
   - `date` is within `advance_booking_days` from today
2. For each matching rule, generate time slots from `start_time` to `end_time` at `slot_interval_minutes` intervals. Each slot = `(time, access_rule_id)`.
3. For each slot, count existing reservations (status in `pending`, `confirmed`, `arrived`, `partially_arrived`, `seated`) at that `(venue_id, date, time)` linked to that access rule.
4. Exclude slots where total covers >= `max_covers_per_slot` (if set).
5. Exclude slots within `cutoff_minutes` of the current time (using venue timezone).
6. Return flat list of `AvailableSlot(time, access_rule_id, access_rule_name)` sorted by time.

**Response schema** (`backend/app/schemas/availability.py`):
```python
class AvailableSlot(BaseModel):
    time: time
    access_rule_id: UUID
    access_rule_name: str

class AvailabilityResponse(BaseModel):
    venue_id: UUID
    date: date
    party_size: int
    slots: list[AvailableSlot]
```

### Task 2B.5 — Availability API Endpoint

**File**: Add to `backend/app/api/v1/reservations.py` (or a dedicated `availability.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/venues/{venue_id}/availability?date=YYYY-MM-DD&party_size=N` | public* | Get available slots |

*Public for the booking widget flow. Auth optional — if authenticated, staff can see more detail.

Query params: `date` (required), `party_size` (required, default 2).

---

## Phase 2C — Reservation CRUD & Status Machine

**Goal**: Create, read, update, and cancel reservations with enforced status transitions.

### Task 2C.1 — Reservation Pydantic Schemas

**File**: `backend/app/schemas/reservation.py`

| Schema | Purpose |
|--------|---------|
| `ReservationCreate` | Guest-facing: `venue_id`, `date`, `time`, `party_size`, `guest info`, `access_rule_id`, `special_requests`, `source` |
| `ReservationUpdate` | Staff-facing: `table_id`, `notes`, `party_size` |
| `ReservationStatusUpdate` | `status` only — enforced via status machine |
| `ReservationRead` | Full representation with nested guest name, table label, access rule name |
| `ReservationCancel` | Optional `reason` field |

Key validations:
- `party_size >= 1`
- `date` not in the past
- `status` transitions validated (see 2C.3)

### Task 2C.2 — Reservation Service Layer

**File**: `backend/app/services/reservation.py`

Functions:
- `create_reservation(db, venue_id, data) → Reservation`
  - Validates slot availability (calls availability engine)
  - Creates or matches GuestProfile (see Phase 2E)
  - Sets initial status: `confirmed` (or `pending` if deposit required)
- `list_reservations(db, venue_id, date, status, page, per_page) → (list, total)`
  - Filterable by date, status, guest name search
  - Eager-loads guest name, table label
- `get_reservation(db, reservation_id) → Reservation`
- `update_reservation(db, reservation_id, data) → Reservation`
  - Allows updating: `table_id`, `notes`, `party_size`, `special_requests`
- `update_status(db, reservation_id, new_status) → Reservation`
  - Validates transition (see 2C.3)
  - Side effects: if `completed` → auto-create GuestVisit
- `cancel_reservation(db, reservation_id) → Reservation`
  - Sets status to `cancelled`, records `cancelled_at`

### Task 2C.3 — Reservation Status Machine

**File**: `backend/app/services/reservation.py` (or `backend/app/services/status_machine.py`)

Define allowed transitions as a constant:

```python
VALID_TRANSITIONS = {
    "pending":              {"confirmed", "cancelled"},
    "confirmed":            {"arrived", "partially_arrived", "cancelled", "no_show"},
    "arrived":              {"seated", "cancelled", "no_show"},
    "partially_arrived":    {"seated", "cancelled", "no_show"},
    "seated":               {"completed"},
    "completed":            set(),      # terminal
    "no_show":              set(),      # terminal
    "cancelled":            set(),      # terminal
}
```

`validate_transition(current, target) → bool` raises `HTTPException(409)` with a clear message on invalid transitions.

**Side effects on transition**:
- `→ completed`: Auto-create `GuestVisit` record (venue_id, guest_id, reservation_id, visited_at=now).
- `→ cancelled`: Set `cancelled_at = utcnow()`.
- `→ no_show`: Optionally log for future auto-tag engine.

### Task 2C.4 — Reservation API Endpoints

**File**: `backend/app/api/v1/reservations.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/venues/{venue_id}/reservations` | staff+ | List reservations, filter by date/status |
| POST | `/venues/{venue_id}/reservations` | public or staff | Create reservation |
| GET | `/reservations/{id}` | staff+ | Get single reservation |
| PATCH | `/reservations/{id}` | staff+ | Update fields (table, notes, party size) |
| PATCH | `/reservations/{id}/status` | staff+ | Advance status (uses status machine) |
| POST | `/reservations/{id}/cancel` | public or staff | Cancel reservation |

Register sub-router in `backend/app/api/v1/router.py`.

**Pagination**: GET list endpoint supports `?page=1&per_page=25` with meta in envelope.

**Filters on list endpoint**:
- `date` (required for staff view — defaults to today)
- `status` (optional, comma-separated: `?status=confirmed,arrived`)
- `search` (optional — matches guest first/last name)

---

## Phase 2D — Waitlist CRUD

**Goal**: Host stand can add walk-ins to a waitlist and manage their flow.

### Task 2D.1 — Waitlist Pydantic Schemas

**File**: `backend/app/schemas/waitlist.py`

| Schema | Purpose |
|--------|---------|
| `WaitlistEntryCreate` | `venue_id`, `party_size`, `guest info` (name, phone), `quoted_wait_minutes`, `notes` |
| `WaitlistEntryUpdate` | `status`, `notes`, `quoted_wait_minutes` |
| `WaitlistEntryRead` | Full representation with nested guest name |

### Task 2D.2 — Waitlist Service Layer

**File**: `backend/app/services/waitlist.py`

Functions:
- `add_to_waitlist(db, venue_id, data) → WaitlistEntry`
  - Creates or matches GuestProfile (by phone or name if no email)
  - Sets `check_in_time = utcnow()`
  - Sets `status = "waiting"`
- `list_waitlist(db, venue_id, active_only=True) → list[WaitlistEntry]`
  - `active_only=True` filters to `status in (waiting, notified)`
  - Ordered by `check_in_time` ASC (FIFO)
- `update_waitlist_entry(db, entry_id, data) → WaitlistEntry`
  - Status transitions: `waiting → notified → seated`, or `waiting/notified → cancelled/no_show`
- `seat_from_waitlist(db, entry_id, table_id?) → (WaitlistEntry, Reservation?)`
  - Updates entry status to `seated`, sets `seated_time`
  - Optionally creates a Reservation with `source="walk_in"` and `status="seated"`

### Task 2D.3 — Waitlist API Endpoints

**File**: `backend/app/api/v1/waitlist.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/venues/{venue_id}/waitlist` | staff+ | List active waitlist entries |
| POST | `/venues/{venue_id}/waitlist` | staff+ | Add guest to waitlist |
| PATCH | `/waitlist/{id}` | staff+ | Update entry (status, notes, wait time) |

Register sub-router in `backend/app/api/v1/router.py`.

---

## Phase 2E — Guest Profile Auto-Creation

**Goal**: Every reservation or waitlist entry automatically creates or matches a guest profile. This is the bridge between the booking flow and the CRM.

### Task 2E.1 — Guest Upsert Service

**File**: `backend/app/services/guest.py`

Core function:
```python
async def get_or_create_guest(
    db: AsyncSession,
    org_id: UUID,
    first_name: str,
    last_name: str,
    email: str | None = None,
    phone: str | None = None,
) -> GuestProfile:
```

**Logic**:
1. If `email` is provided: look up by `(org_id, email)`.
   - If found: update `first_name`, `last_name`, `phone` if new values are non-null and existing are null (enrich, don't overwrite).
   - If not found: create new profile.
2. If no email: create new profile every time (phone-based dedup is future scope).
3. Return the profile.

This function is called by:
- `reservation.create_reservation()` — with guest info from the booking form
- `waitlist.add_to_waitlist()` — with guest info from the host stand

### Task 2E.2 — Minimal Guest Schemas

**File**: `backend/app/schemas/guest.py`

| Schema | Purpose |
|--------|---------|
| `GuestInfo` | Embedded in ReservationCreate: `first_name`, `last_name`, `email`, `phone`, `special_requests` |
| `GuestRead` | Read representation for nesting in reservation/waitlist responses |

Full guest CRUD endpoints are Phase 4 scope but the schemas serve as the foundation.

---

## Phase 2F — Staff Reservation View (Frontend)

**Goal**: Staff dashboard showing today's reservations with status management.

### Task 2F.1 — Frontend Project Setup

Establish the frontend patterns used across all Phase 2 UI work.

**Files**:
- `frontend/src/lib/api.ts` — API client wrapper (fetch-based, handles auth token, base URL from env, parses envelope)
- `frontend/src/lib/types.ts` — TypeScript types mirroring backend schemas: `Reservation`, `WaitlistEntry`, `AccessRule`, `AvailableSlot`, `Guest`, `Venue`
- `frontend/src/lib/utils.ts` — Date formatting, timezone conversion helpers
- `frontend/src/components/ui/` — Shared UI primitives: Button, Input, Select, Badge, Card, Modal, DatePicker (built with Tailwind, no component library)

### Task 2F.2 — Auth Pages

**Files**:
- `frontend/src/app/login/page.tsx` — Login form → stores JWT in httpOnly cookie or localStorage
- `frontend/src/app/register/page.tsx` — Register org + owner
- `frontend/src/lib/auth.ts` — Auth context/provider, token storage, refresh logic
- Middleware or layout guard to redirect unauthenticated users

### Task 2F.3 — Dashboard Layout

**File**: `frontend/src/app/dashboard/layout.tsx`

- Sidebar navigation: Reservations, Waitlist, Floor Plans (future), Guests (future), Settings
- Top bar: venue selector dropdown (org can have multiple venues), user menu
- Venue context stored in URL or state — all child pages operate on the selected venue

### Task 2F.4 — Reservations List Page

**File**: `frontend/src/app/dashboard/reservations/page.tsx`

**Features**:
- Date picker (defaults to today) — fetches reservations for selected date
- Status filter tabs: All | Upcoming | Seated | Completed | Cancelled
- Table/list view showing: time, guest name, party size, table assignment, status badge, notes preview
- Click row → opens reservation detail panel/modal
- "New Reservation" button → opens creation form (see 2F.5)
- Auto-refresh on interval (30s) or manual refresh button

**API calls**: `GET /venues/{venue_id}/reservations?date=YYYY-MM-DD&status=...`

### Task 2F.5 — Reservation Detail & Status Actions

**File**: `frontend/src/components/reservations/ReservationDetail.tsx`

- Shows full reservation details: guest info, party size, time, table, access rule, notes, special requests, status history
- **Status action buttons** — contextual based on current status:
  - `confirmed` → "Mark Arrived", "No Show", "Cancel"
  - `arrived` → "Seat" (opens table selector), "No Show"
  - `seated` → "Complete"
- Table assignment dropdown (fetches tables from venue's floor plans)
- Inline edit for notes and party size
- Cancel button with confirmation dialog

**API calls**: `PATCH /reservations/{id}/status`, `PATCH /reservations/{id}`

### Task 2F.6 — Create Reservation Form (Staff-Side)

**File**: `frontend/src/components/reservations/CreateReservationForm.tsx`

Staff-facing form for manual booking (phone call, walk-in conversion):
1. Select date + party size
2. System calls availability API → shows available time slots
3. Staff selects slot
4. Enter guest info (first name, last name, email, phone)
5. Add notes / special requests
6. Submit → creates reservation

**API calls**: `GET /venues/{venue_id}/availability`, `POST /venues/{venue_id}/reservations`

### Task 2F.7 — Waitlist View

**File**: `frontend/src/app/dashboard/waitlist/page.tsx`

- List of active waitlist entries ordered by check-in time (FIFO)
- Each row: guest name, party size, wait time (quoted + elapsed), status badge
- Actions per entry:
  - "Notify" → status `notified`
  - "Seat" → status `seated` (with optional table selector)
  - "Cancel" / "No Show"
- "Add to Waitlist" button → simple form: guest name, phone, party size, quoted wait

**API calls**: `GET /venues/{venue_id}/waitlist`, `POST /venues/{venue_id}/waitlist`, `PATCH /waitlist/{id}`

---

## Phase 2G — Booking Widget (Frontend)

**Goal**: A guest-facing booking component that can be embedded on a restaurant's website.

### Task 2G.1 — Widget Page

**File**: `frontend/src/app/book/[venue_id]/page.tsx`

A standalone, publicly accessible booking page (no auth required). This page is the V1 booking widget — a full-page flow rather than an iframe embed. The embed strategy (iframe vs Web Component) is an open question deferred to post-V1.

**Flow** (multi-step form):
1. **Date & Party Size** — date picker + party size selector (1-20)
2. **Time Slot Selection** — calls availability API, displays available slots as selectable cards/buttons grouped by meal period (derived from access rule name)
3. **Guest Information** — first name, last name, email (required), phone, special requests
4. **Confirmation** — summary of booking details, cancellation policy text (from access rule), "Confirm Booking" button
5. **Success** — confirmation screen with reservation details

### Task 2G.2 — Widget Styling & Theming

- Clean, minimal design using Tailwind
- Supports basic theming via URL params: `?primaryColor=hex&fontFamily=name`
- Mobile-responsive (majority of guest bookings happen on mobile)
- No auth required — this is a public page
- Venue name and branding displayed at the top (fetched from venue API)

### Task 2G.3 — Widget API Integration

The widget calls two endpoints:
1. `GET /venues/{venue_id}/availability?date=...&party_size=...` — fetches slots
2. `POST /venues/{venue_id}/reservations` — creates reservation (with inline guest info)

Both endpoints must work without authentication for the widget flow. The POST endpoint creates/matches the guest profile server-side (Task 2E.1).

---

## Implementation Order

The tasks above have dependencies. Follow this sequence:

```
2A.1  API Envelope
2A.2  Auth & JWT           ← depends on nothing
2A.3  Org/Venue/User CRUD  ← depends on 2A.1, 2A.2
2A.4  Alembic Migration    ← depends on nothing (models exist)
2A.5  Seed Data            ← depends on 2A.4
  │
  ▼
2B.1  Access Rule Schemas
2B.2  Access Rule Service   ← depends on 2B.1
2B.3  Access Rule Endpoints ← depends on 2B.2, 2A.1, 2A.2
2B.4  Availability Engine   ← depends on 2B.2
2B.5  Availability Endpoint ← depends on 2B.4
  │
  ▼
2E.1  Guest Upsert Service  ← depends on nothing (uses existing model)
2E.2  Guest Schemas
  │
  ▼
2C.1  Reservation Schemas
2C.2  Reservation Service   ← depends on 2B.4 (availability), 2E.1 (guest upsert)
2C.3  Status Machine        ← depends on nothing
2C.4  Reservation Endpoints ← depends on 2C.1-3, 2A.1, 2A.2
  │
  ▼
2D.1  Waitlist Schemas
2D.2  Waitlist Service      ← depends on 2E.1 (guest upsert)
2D.3  Waitlist Endpoints    ← depends on 2D.1-2, 2A.1, 2A.2
  │
  ▼
2F.1  Frontend Setup        ← depends on backend endpoints existing
2F.2  Auth Pages            ← depends on 2A.2
2F.3  Dashboard Layout
2F.4  Reservations List     ← depends on 2C.4
2F.5  Reservation Detail    ← depends on 2C.4
2F.6  Create Reservation    ← depends on 2B.5, 2C.4
2F.7  Waitlist View         ← depends on 2D.3
  │
  ▼
2G.1  Booking Widget Page   ← depends on 2B.5, 2C.4
2G.2  Widget Styling
2G.3  Widget API Integration
```

---

## File Summary

All new files to be created in Phase 2:

### Backend — Schemas (`backend/app/schemas/`)
| File | Contents |
|------|----------|
| `envelope.py` | `Envelope[T]`, `PaginatedEnvelope[T]`, `ErrorDetail`, helpers |
| `access_rule.py` | `AccessRuleCreate`, `AccessRuleUpdate`, `AccessRuleRead` |
| `availability.py` | `AvailableSlot`, `AvailabilityResponse` |
| `reservation.py` | `ReservationCreate`, `ReservationUpdate`, `ReservationStatusUpdate`, `ReservationRead`, `ReservationCancel` |
| `waitlist.py` | `WaitlistEntryCreate`, `WaitlistEntryUpdate`, `WaitlistEntryRead` |
| `guest.py` | `GuestInfo`, `GuestRead` |
| `organization.py` | `OrgRead`, `OrgUpdate` |
| `venue.py` | `VenueCreate`, `VenueUpdate`, `VenueRead` |
| `user.py` | `UserCreate`, `UserUpdate`, `UserRead` |
| `auth.py` | `RegisterRequest`, `LoginRequest`, `TokenResponse` |

### Backend — Services (`backend/app/services/`)
| File | Contents |
|------|----------|
| `access_rule.py` | Access rule CRUD logic |
| `availability.py` | Slot generation algorithm |
| `reservation.py` | Reservation CRUD + status machine |
| `waitlist.py` | Waitlist management |
| `guest.py` | `get_or_create_guest()` upsert |

### Backend — API Routes (`backend/app/api/v1/`)
| File | Contents |
|------|----------|
| `auth.py` | Register, login, refresh |
| `organizations.py` | GET/PATCH org |
| `venues.py` | Venue CRUD |
| `users.py` | User CRUD |
| `access_rules.py` | Access rule CRUD |
| `reservations.py` | Reservation CRUD + availability + status |
| `waitlist.py` | Waitlist CRUD |

### Backend — Core (`backend/app/core/`)
| File | Contents |
|------|----------|
| `security.py` | JWT creation/verification, password hashing |
| `dependencies.py` | `get_current_user`, `get_current_org`, `require_role` |

### Backend — Scripts
| File | Contents |
|------|----------|
| `backend/scripts/seed.py` | Demo data seeder |

### Frontend
| File | Contents |
|------|----------|
| `src/lib/api.ts` | API client |
| `src/lib/types.ts` | TypeScript type definitions |
| `src/lib/utils.ts` | Formatting helpers |
| `src/lib/auth.ts` | Auth context, token management |
| `src/components/ui/*.tsx` | Shared UI primitives |
| `src/app/login/page.tsx` | Login page |
| `src/app/register/page.tsx` | Registration page |
| `src/app/dashboard/layout.tsx` | Dashboard shell (sidebar, venue selector) |
| `src/app/dashboard/reservations/page.tsx` | Reservation list view |
| `src/components/reservations/ReservationDetail.tsx` | Detail panel + status actions |
| `src/components/reservations/CreateReservationForm.tsx` | Staff booking form |
| `src/app/dashboard/waitlist/page.tsx` | Waitlist view |
| `src/app/book/[venue_id]/page.tsx` | Public booking widget |

---

## Exit Criteria

Phase 2 is complete when ALL of the following are true:

- [ ] Access rules can be created and managed per venue via API
- [ ] Availability engine returns correct open slots given date + party size, respecting pacing limits and cutoff times
- [ ] Reservations can be created, listed (filtered by date/status), and updated via API
- [ ] Status machine enforces valid transitions (`pending → confirmed → arrived → seated → completed`)
- [ ] Cancellation sets `cancelled_at` and transitions to `cancelled` status
- [ ] `completed` transition auto-creates a `GuestVisit` record
- [ ] Waitlist entries can be added, listed, and status-updated via API
- [ ] Guest profiles are auto-created/matched on reservation and waitlist creation
- [ ] Staff can log in and see a daily reservation view in the frontend
- [ ] Staff can advance reservation statuses and assign tables from the UI
- [ ] Staff can manage the waitlist from the UI
- [ ] A guest can complete the booking widget flow: select date → party size → time slot → enter info → confirm
- [ ] Booking widget creates a reservation and guest profile server-side
- [ ] All endpoints return the standard API envelope format
- [ ] Seed data script populates a usable demo environment
