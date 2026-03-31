# Changelog

---

## Index

### 0.7.7 — Pre-Phase 3 Quality Review Round 5 (2026-03-31)
### 0.7.6 — Pre-Phase 3 Quality Review Round 4 (2026-03-31)
### 0.7.5 — Pre-Phase 3 Quality Review Round 3 (2026-03-31)
### 0.7.4 — Pre-Phase 3 Quality Review Round 2 (2026-03-31)
### 0.7.3 — Pre-Phase 3 Quality Review (2026-03-31)
### 0.7.2 — Post-Phase 2 Production Readiness (2026-03-31)
### 0.7.1 — Phase 2H: Code Quality & Security Hardening (2026-03-31)
### 0.7.0 — Phase 2G: Booking Widget (2026-03-31)
### 0.6.0 — Phase 2F: Staff Dashboard (Frontend) (2026-03-31)
### 0.5.0 — Phase 2D: Waitlist CRUD (2026-03-31)
### 0.4.0 — Phase 2C+2E: Reservations & Guest Auto-Creation (2026-03-31)
### 0.3.0 — Phase 2B: Access Rules & Availability Engine (2026-03-31)
### 0.2.0 — Phase 2A: Backend Foundation (2026-03-31)
### 0.1.0 — Project Scaffold (2026-03-30)

---

## 0.7.7 — Pre-Phase 3 Quality Review Round 5

**Date**: 2026-03-31

Fifth quality review pass addressing 12 findings (3 high, 5 medium, 4 low) across backend, frontend, and infrastructure. Focuses on data integrity constraints, waitlist concurrency, and frontend resilience. Full details in [`docs/completions/pre-phase-3-quality-review-5-completion.md`](completions/pre-phase-3-quality-review-5-completion.md).

### Backend (8 fixes)
- **Waitlist FOR UPDATE locks** — `update_waitlist_entry` and `seat_from_waitlist` now acquire row-level locks before status transitions, matching the reservation locking pattern
- **Org slug partial unique index** — soft-deleted orgs no longer block slug reuse (mirrors users.email fix from 0003)
- **DB CHECK constraints** — survey ratings (1-5), table capacity (min <= max), access rule time/date ordering, reservation/waitlist status enums
- **Slug format validation** — regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` on all org/venue slug fields
- **FK indexes** — `users.org_id`, `tags.org_id`, `guest_profiles.org_id`, `guest_visits.guest_id`, `guest_visits.venue_id`
- **Seating areas validation** — max 20 items, max 100 chars per item on access rule seating_areas
- **LoginRequest password min_length** — consistent with RegisterRequest (min_length=8)

### Frontend (3 fixes)
- **Booking widget AbortController** — venue fetch useEffect now cleans up on unmount/dependency change
- **Booking widget ErrorBoundary** — new layout wrapping the widget in the existing ErrorBoundary component
- **Polling exponential backoff** — reservations and waitlist pages now back off on failure (1.5x multiplier, 5min cap) instead of fixed-interval polling

### Infrastructure (1 fix)
- **Frontend prod healthcheck** — `docker-compose.prod.yml` frontend service now has full healthcheck with `start_period: 15s`

### Migration
- `0005_data_integrity_hardening` — org slug partial index, 10 CHECK constraints, 5 FK indexes

---

## 0.7.6 — Pre-Phase 3 Quality Review Round 4

**Date**: 2026-03-31

Fourth quality review pass addressing 6 findings (2 high, 4 medium) across backend and frontend. Focuses on concurrency safety under production load, timezone correctness, and input validation consistency. Full details in [`docs/completions/pre-phase-3-quality-review-4-completion.md`](completions/pre-phase-3-quality-review-4-completion.md).

### Backend (5 fixes)
- **Party-size update overbooking race** — `update_reservation` party-size validation now acquires `FOR UPDATE` lock on sibling reservations, preventing concurrent increases from exceeding slot capacity
- **Availability `today` uses venue timezone** — `get_available_slots` now uses `ZoneInfo(venue_timezone)` instead of `date.today()` for advance booking window calculation
- **`seat_from_waitlist` table-venue validation** — added `Table → FloorPlan → venue_id` join check before creating walk-in reservation
- **Slug TOCTOU → 409** — venue create/update and org update now catch `IntegrityError` on concurrent slug collisions, returning HTTP 409 instead of 500
- **Pagination params validated** — `list_users` and `list_venues` now use `Query(ge=1, le=100)` consistent with all other paginated endpoints

### Frontend (1 fix)
- **Booking widget hex regex** — tightened from `{3,8}` to exact 3/6/8 character match, rejecting invalid CSS hex lengths

---

## 0.7.5 — Pre-Phase 3 Quality Review Round 3

**Date**: 2026-03-31

Third quality review pass addressing 23 findings (1 critical, 8 high, 14 medium) across backend, frontend, and infrastructure. Full details in [`docs/completions/pre-phase-3-quality-review-3-completion.md`](completions/pre-phase-3-quality-review-3-completion.md).

### Backend (12 fixes)
- **CRITICAL: Guest upsert SAVEPOINT** — `get_or_create_guest` now uses `begin_nested()` instead of `db.rollback()`, preserving the outer transaction and FOR UPDATE locks
- **Survey IDOR prevention** — `create_survey` validates `guest_id` and `reservation_id` belong to the correct org/venue
- **Health endpoint info leak** — `/health/ready` no longer returns exception details; logs server-side instead
- **Cancel reservation row lock** — `cancel_reservation` now acquires `FOR UPDATE` lock, matching `update_status`
- **`seat_from_waitlist` endpoint** — new `POST /waitlist/{entry_id}/seat` wires the existing service function to an API route
- **Cross-venue table validation** — `update_reservation` now verifies the table belongs to the reservation's venue via FloorPlan join
- **LIKE wildcard escaping** — guest name search now escapes `%`, `_`, `\` in LIKE patterns
- **Availability party_size cap** — raised from 20 to 100 to match configurable access rule bounds
- **AccessRule schema bounds** — added `ge`/`le` constraints on all numeric fields; `party_size` capped at 100 on reservation schemas
- **Deterministic SQL** — converted set literals in `.in_()` calls to lists for consistent prepared statement caching
- **Slug uniqueness `is_active` filter** — org update and venue creation now exclude soft-deleted entities
- **alembic.ini credentials** — replaced hardcoded dev credentials with a placeholder

### Frontend (10 fixes)
- **401 handler fall-through** — added explicit `throw` after redirect to prevent error flash
- **Modal focus trap + scroll lock** — keyboard focus cycles within the dialog; body scroll disabled when open; unique `aria-labelledby` IDs via `useId()`
- **Stale reservation modal** — detail modal now syncs with latest polled data instead of showing click-time snapshot
- **AuthProvider stable refs** — `login`/`register`/`logout` wrapped in `useCallback`, context value in `useMemo`; same for VenueProvider
- **`today()` timezone fix** — now uses local date components instead of UTC-based `toISOString()`
- **Waitlist modal form reset** — form state resets on modal open, not just on successful submission
- **Refresh button signal fix** — both pages now use `() => fetch()` instead of passing MouseEvent as AbortSignal
- **Card keyboard accessibility** — interactive cards get `role="button"`, `tabIndex`, and Enter/Space handlers
- **Input unique IDs** — replaced label-derived IDs with React's `useId()` hook
- **Booking widget loading state** — removed wasteful pre-warm fetch; added loading indicator; fixed non-null assertion

### Infrastructure (1 fix)
- **Production port exposure** — `docker-compose.prod.yml` now clears port mappings for backend (8000) and frontend (3000)

---

## 0.7.4 — Pre-Phase 3 Quality Review Round 2

**Date**: 2026-03-31

Second quality review pass addressing 10 findings (5 critical, 5 high) across backend and frontend. Full details in [`docs/completions/pre-phase-3-quality-review-2-completion.md`](completions/pre-phase-3-quality-review-2-completion.md).

### Backend (7 fixes)
- **Table capacity validation** — reservation updates now reject party sizes outside table min/max capacity (HTTP 409)
- **Survey CRUD endpoints** — `GET/POST /venues/{id}/surveys`, `GET /surveys/{id}` (staff+)
- **FloorPlan & Table CRUD endpoints** — 6 new endpoints for managing floor plans and tables (admin+/manager+)
- **Walk-in cancel_token** — `seat_from_waitlist` now generates cryptographic cancel token for walk-in reservations
- **AccessRuleUpdate deposit cross-validation** — partial updates now validate require_deposit + deposit_amount against existing DB values
- **Waitlist/Survey schema bounds** — `quoted_wait_minutes` capped at 0–480, `comment` max 5000 chars, `TableCreate` validates min <= max capacity
- **Query indexes** — composite indexes on `waitlist(venue_id, status)`, `reservations(venue_id, status)`, `reservations(guest_id)`

### Frontend (3 fixes)
- **Deduplicated token functions** — `storeTokens`/`clearTokens` centralized in `api.ts`, removed from `auth.ts`
- **AbortController on dashboard fetches** — reservations and waitlist pages cancel in-flight requests on unmount
- **Shared publicFetch** — booking widget now imports from `lib/api.ts` instead of defining its own fetch

### Migration
- `0004_add_query_indexes` — three new indexes for query performance

---

## 0.7.3 — Pre-Phase 3 Quality Review

**Date**: 2026-03-31

Comprehensive quality review addressing 20 findings across backend, frontend, and infrastructure. Full details in [`docs/completions/pre-phase-3-quality-review-completion.md`](completions/pre-phase-3-quality-review-completion.md).

### Backend (10 fixes)
- **Partial unique index** on `users.email` — soft-deleted users no longer block email reuse
- **Connection pooling** — `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`
- **Cancel token indexed** — prevents full table scan on public cancel endpoint
- **Access rule active check** — reservation creation now rejects deactivated rules (HTTP 409)
- **selectinload pagination** — replaced `joinedload` to fix LIMIT interaction; deduplicated filter logic
- **Timezone validation** — invalid IANA timezone strings rejected at venue creation/update
- **Party size re-validation** — `PATCH /reservations` checks slot capacity before accepting new party size
- **Rate limiting** — `slowapi` on auth (5-20/min), availability (30/min), booking (10/min)
- **Readiness endpoint** — `/health/ready` verifies DB connectivity (503 on failure)
- **AccessRuleUpdate cross-field validation** — partial updates validated against existing DB values

### Frontend (5 fixes)
- Replaced `alert()` with inline error state on waitlist page
- Type-safe 204 response handling; `api.delete` typed as `request<null>`
- Token refresh mutex prevents concurrent refresh calls from desynchronising tokens
- Non-null assertion replaced with explicit null guard on reservation form
- `ErrorBoundary` component wraps dashboard content for graceful crash recovery

### Infrastructure (5 fixes)
- Uvicorn runs 4 workers in Docker (`--workers 4`)
- Dependency versions tightened: `^` → `~` (frontend), narrower ranges (backend)
- `docker-compose.prod.yml` overlay with resource limits, restart policies, and secret management
- Seed script refuses to run when `ENVIRONMENT=production`
- Added `backend/.env.example` documenting all required production variables

### Migration
- `0003_quality_hardening` — partial unique index on `users.email`, index on `reservations.cancel_token`

---

## 0.7.2 — Post-Phase 2 Production Readiness

**Date**: 2026-03-31

Full-stack production-readiness pass addressing 16 findings from comprehensive code review. Full details in [`docs/completions/post-phase-2-fixes-completion.md`](completions/post-phase-2-fixes-completion.md).

### Security (Critical)
- SECRET_KEY validation — app refuses to start in production with default key; warns in development
- Restricted CORS `allow_methods` and `allow_headers` from wildcards to explicit lists
- Added security headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`
- Removed `cancel_token` from `ReservationRead` API responses (was leaking IDOR protection token)

### Data Integrity
- Added `IntegrityError` handling on registration and user creation (concurrent duplicate emails → 409, not 500)
- Soft-deleted users no longer block email reuse (uniqueness checks now filter by `is_active`)

### API Consistency
- Global `HTTPException` handler wraps all errors in the `{ data, meta, errors }` envelope format

### Observability
- Added structured audit logging: auth events (register, login success/failure), reservation lifecycle (create, status change, cancel), waitlist operations (add, status change)

### Infrastructure
- Backend Dockerfile: multi-stage build (no gcc in final image), non-root `appuser`
- Added healthchecks for backend (`/health`) and frontend containers
- Created `.dockerignore` for both services
- Pinned dependency version ranges (`>=X,<Y`) in `requirements.txt`

### Frontend
- Client-side email/phone validation on booking widget before submission
- Accessibility: `role="dialog"` + `aria-modal` on Modal, `role="tablist/tab"` + `aria-selected` on status tabs, `role="radiogroup/radio"` + `aria-checked` on party size selectors, `role="alert"` on all error messages, `aria-label` + focus ring on table rows

---

## 0.7.1 — Phase 2H: Code Quality & Security Hardening

**Date**: 2026-03-31

Comprehensive review and hardening pass across all Phase 2 code. Full details in [`docs/completions/phase-2h-completion.md`](completions/phase-2h-completion.md).

### Security
- Fixed IDOR on public cancel endpoint — now requires cryptographic `cancel_token` query parameter
- Added CSS injection prevention on booking widget `primaryColor` URL param
- Centralised token cleanup on logout to clear stale venue preferences

### Concurrency & Data Integrity
- Added `SELECT FOR UPDATE` lock on slot availability check to prevent overbooking
- Added `IntegrityError` handling on guest upsert for concurrent deduplication
- Added row-level locking on reservation status transitions
- Made `seat_from_waitlist` atomic (single flush for waitlist + reservation)

### Frontend Reliability
- Implemented automatic token refresh with single-retry on 401
- Added JSON parse error handling in both authenticated and public API clients
- Added error state display to reservations page, waitlist page, and venue context
- Fixed auth guard race condition (loading vs. redirect timing)
- Replaced `window.location.href` with `router.push()` for SPA navigation

### Validation & Schemas
- Added `max_length` constraints to all string input fields across schemas
- Added `min_length=8` password requirement on register and user create
- Added missing `require_deposit` cross-field validation to `AccessRuleUpdate`
- Fixed UUID parse error in `get_current_user` (500 → 401)
- Added pagination tiebreaker (`Reservation.id`) to prevent non-deterministic ordering
- Created schemas for Survey (with rating range validation), FloorPlan/Table, and Tag (with hex color validation)

### API Completeness
- Added `GET /access-rules/{rule_id}` endpoint
- Added `DELETE /waitlist/{entry_id}` endpoint
- Reduced default `per_page` from 100 to 50 on reservations page

### Accessibility
- Added `aria-label` to Modal close button
- Added keyboard navigation (Enter/Space) to reservation table rows

---

## 0.7.0 — Phase 2G: Booking Widget

**Date**: 2026-03-31

Guest-facing booking widget — completes Phase 2. Full details in [`docs/completions/phase-2g-completion.md`](completions/phase-2g-completion.md).

### Public Booking Page
- 5-step flow at `/book/{venue_id}`: date & party size → time slot selection → guest info → confirmation → success
- Slots grouped by meal period (access rule name) in a 3-column touch-friendly grid
- Mobile-first `max-w-md` card layout — works on any device
- Venue name and address displayed from public API

### Theming
- URL-based: `?primaryColor=hex` sets primary button color
- Any hex value works without compile-time changes

### API Integration
- Standalone `publicFetch` — no auth context, no JWT
- Only two endpoints: availability check + reservation create
- All bookings tagged `source: "widget"` for channel analytics
- Email required (ensures guest profile deduplication)

### Phase 2 Complete
All exit criteria met. End-to-end flow: guest books via widget → staff manages from dashboard → reservation progresses through status machine → visit recorded in CRM.

---

## 0.6.0 — Phase 2F: Staff Dashboard (Frontend)

**Date**: 2026-03-31

Staff-facing dashboard for managing reservations and waitlist. Full details in [`docs/completions/phase-2f-completion.md`](completions/phase-2f-completion.md).

### Foundation
- Fetch-based API client with auto JWT injection and envelope parsing
- TypeScript types mirroring all backend schemas
- 6 UI primitives (Button, Input, Select, Badge, Modal, Card) — all Tailwind, no component library
- Auth context (login, register, logout, token management in localStorage)
- Venue context (auto-loads venues, persists selection across refreshes)

### Auth Pages
- Login and register pages with error handling
- Register auto-generates URL slug from organization name
- Dashboard layout acts as auth guard — redirects to login if unauthenticated

### Dashboard Layout
- Fixed sidebar (224px) with nav links and venue selector for multi-venue orgs
- Top bar with user name and sign-out

### Reservations
- Daily reservation list with date picker and status filter tabs (All/Upcoming/Seated/Completed/Cancelled)
- Table view with time, guest, party size, table, status badge, notes
- Click-to-open detail modal with contextual status action buttons (Confirm/Arrive/Seat/Complete/Cancel/No Show)
- 4-step staff booking form: date+party → slot selection (grouped by meal period) → guest info → confirm
- 30-second auto-refresh

### Waitlist
- Card-based FIFO list with party size, guest name, elapsed/quoted wait time
- Inline Notify/Seat/No Show action buttons
- Add-to-waitlist modal with party size picker and quoted wait input
- 15-second auto-refresh

---

## 0.5.0 — Phase 2D: Waitlist CRUD

**Date**: 2026-03-31

Walk-in guest management from check-in to seating. Full details in [`docs/completions/phase-2d-completion.md`](completions/phase-2d-completion.md).

### Waitlist Management
- Add walk-ins with guest info, party size, and quoted wait time
- FIFO-ordered active list (waiting + notified), with option to show all
- Status machine: `waiting → notified → seated` (plus `cancelled`/`no_show` exits)
- Auto-records `seated_time` for wait-time analytics
- Guest upsert on add — walk-ins get CRM profiles just like online bookings

### Walk-in → Reservation Bridge
- `seat_from_waitlist` with a table ID creates a `Reservation(source="walk_in", status="seated")`
- Walk-ins appear alongside bookings in the reservation list — uniform tracking

### All Staff-Only
- All 3 endpoints require `staff+` auth (unlike reservations which have public create/cancel)
- Org-scoped via venue ownership verification

---

## 0.4.0 — Phase 2C+2E: Reservations & Guest Auto-Creation

**Date**: 2026-03-31

Full reservation lifecycle and automatic guest profile management. Full details in [`docs/completions/phase-2c-2e-completion.md`](completions/phase-2c-2e-completion.md).

### Guest Auto-Creation (2E)
- `get_or_create_guest()` upsert — matches by `(org_id, email)`, enriches without overwriting staff corrections
- `GuestInfo` schema embedded in reservation/waitlist creation requests
- No-email guests always create new profiles (phone-based dedup is future scope)

### Reservation CRUD (2C)
- Create reservation with server-side availability re-validation (prevents race conditions)
- List with date/status/guest-name filters and pagination
- Update mutable fields: table assignment, notes, party size, special requests
- Public create (`POST /venues/{id}/reservations`) and cancel (`POST /reservations/{id}/cancel`) for widget flow
- Staff-only list, get, update, and status endpoints

### Status Machine
- Enforced transitions: `pending→confirmed→arrived→seated→completed` (plus `cancelled` and `no_show` branches)
- HTTP 409 with clear error on invalid transitions
- Side effects: `→completed` auto-creates GuestVisit; `→cancelled` sets `cancelled_at` and appends reason to notes

---

## 0.3.0 — Phase 2B: Access Rules & Availability Engine

**Date**: 2026-03-31

Access rule management and the availability engine. Full details in [`docs/completions/phase-2b-completion.md`](completions/phase-2b-completion.md).

### Access Rules
- Pydantic schemas with cross-field validation (time ordering, party size ranges, slot intervals, deposit requirements)
- Async service layer with full CRUD + soft delete
- REST endpoints: list/create under `/venues/{id}/access-rules`, update/delete at `/access-rules/{id}` (manager+ auth)
- Org-scoping enforced on all operations

### Availability Engine
- Core algorithm in `services/availability.py` — generates bookable slots from rules, existing reservations, and pacing limits
- Pacing counts covers (sum of party sizes), not reservation count — correctly handles mixed party sizes
- Only 2 DB queries total (rules + batch cover counts) regardless of slot count
- Timezone-aware cutoff for same-day bookings via `zoneinfo`
- Public endpoint at `GET /venues/{id}/availability?date=...&party_size=...` (no auth — for booking widget)

---

## 0.2.0 — Phase 2A: Backend Foundation

**Date**: 2026-03-31

Backend infrastructure for auth, CRUD, and data seeding. Full details in [`docs/completions/phase-2a-completion.md`](completions/phase-2a-completion.md).

### API Envelope
- Generic `Envelope[T]` and `PaginatedEnvelope[T]` response wrappers with `data`, `meta`, `errors` structure
- Helper functions `ok()`, `paginated()`, `error()` for consistent endpoint responses

### Auth & JWT
- JWT-based authentication with access + refresh token flow
- Password hashing via bcrypt (passlib)
- Auth endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
- Registration creates Organization + owner User atomically
- Role hierarchy: owner > admin > manager > staff with `require_role()` dependency guard

### Org, Venue, User CRUD
- Organization: GET/PATCH current org (admin+ to update)
- Venues: full CRUD with org-scoped slug uniqueness, pagination, soft delete (admin+ to create/delete, manager+ to update, staff+ to read)
- Users: full CRUD with email uniqueness, pagination, soft delete, self-deletion prevention (admin+ for all management, any authenticated for `/users/me`)
- All endpoints enforce multi-tenancy via `org_id` scoping

### Initial Migration
- Hand-written Alembic migration (`0001_initial_schema`) covering all 12 entities / 13 tables
- FK-ordered creation and reverse-ordered teardown

### Seed Data
- Idempotent `scripts/seed.py` with demo org, 3 users, 2 venues, floor plans, tables, access rules, and 8 guest profiles

---

## 0.1.0 — Project Scaffold

**Date**: 2026-03-30

Initial project scaffold for OpenRooms — an open-source SevenRooms clone focused on core reservation operations.

---

### Backend (FastAPI)

Scaffolded a Python backend at `backend/` using FastAPI with async support.

**App structure:**
- `app/main.py` — FastAPI app entry point with CORS middleware (configurable origins via `CORS_ORIGINS`), health check at `/health`, and API router mounted at `/api/v1`
- `app/core/config.py` — Pydantic Settings configuration loading from `backend/.env`. Supports `DATABASE_URL` (asyncpg for app runtime), `DATABASE_URL_SYNC` (psycopg2 for Alembic), `SECRET_KEY`, `CORS_ORIGINS`, and `ENVIRONMENT`
- `app/core/database.py` — Async SQLAlchemy 2.0 engine and session factory using `asyncpg`. Provides `get_db` dependency for route handlers with auto-commit/rollback. Uses `DeclarativeBase` (SQLAlchemy 2.0 style)
- `app/api/v1/router.py` — Stub API router, ready for sub-routers per resource

**Dependencies** (`requirements.txt`):
- `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `psycopg2-binary`, `alembic`, `pydantic`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `httpx`

**Dockerfile**: Python 3.12-slim base, installs requirements, runs `uvicorn` on port 8000.

---

### Data Model (SQLAlchemy 2.0)

12 entities across 9 model files in `app/models/`. All models use:
- `Mapped[]` type annotations with `mapped_column()` (SQLAlchemy 2.0 style)
- UUID primary keys with `server_default=text("gen_random_uuid()")` (Postgres-native)
- `TimestampMixin` providing `created_at` and `updated_at` with server-side defaults

**Entities:**

| Entity | File | Purpose | Key constraints |
|--------|------|---------|-----------------|
| `Organization` | `organization.py` | Multi-tenant root | `slug` unique |
| `User` | `user.py` | Staff accounts | `email` unique, FK → Organization, role enum (owner/admin/manager/staff) |
| `Venue` | `venue.py` | Restaurant/location | UniqueConstraint on `(org_id, slug)` |
| `GuestProfile` | `guest.py` | Central guest record | UniqueConstraint on `(org_id, email)` |
| `GuestVisit` | `guest.py` | Per-venue visit history | FK → GuestProfile, Venue, Reservation (nullable) |
| `guest_tags` | `guest.py` | Association table | Many-to-many between GuestProfile and Tag |
| `Tag` | `tag.py` | Manual + auto tags | UniqueConstraint on `(org_id, name)`, `is_auto` flag |
| `FloorPlan` | `floor_plan.py` | Venue floor layout | FK → Venue |
| `Table` | `floor_plan.py` | Individual table | FK → FloorPlan, capacity range, x/y position, shape, section |
| `AccessRule` | `reservation.py` | Availability rules | FK → Venue, `ARRAY(Integer)` for days_of_week, `ARRAY(String)` for seating_areas |
| `Reservation` | `reservation.py` | Guest booking | FK → Venue, GuestProfile, Table (nullable), AccessRule (nullable). Composite index on `(venue_id, date)` |
| `WaitlistEntry` | `reservation.py` | Walk-in queue | FK → Venue, GuestProfile. Status: waiting/notified/seated/cancelled/no_show |
| `Survey` | `survey.py` | Post-visit feedback | FK → Venue, GuestProfile, Reservation (nullable). Five rating dimensions (1-5) |

**Multi-tenancy model:**
- `Organization` is the tenant boundary — all data isolation scopes to org
- Guest profiles are org-scoped (shared across all venues within an org)
- A single restaurant is an org with one venue — no special case in the schema

---

### Alembic Migrations

Migration framework configured at `backend/alembic/`:
- `alembic.ini` — Standard config pointing to `alembic/` directory
- `alembic/env.py` — Imports all models via `app.models`, overrides connection URL with `settings.DATABASE_URL_SYNC` (sync psycopg2 driver). Supports both online and offline migration modes
- `alembic/script.py.mako` — Standard migration template
- `alembic/versions/` — Empty, ready for initial migration generation via `alembic revision --autogenerate`

---

### Frontend (Next.js)

Scaffolded a TypeScript frontend at `frontend/` using Next.js 15 with the App Router.

**Structure:**
- `src/app/layout.tsx` — Root layout with metadata (title: "OpenRooms")
- `src/app/page.tsx` — Landing page with project description and V1 feature badges
- `src/app/globals.css` — Tailwind CSS 4 import
- `next.config.ts` — Minimal config with `output: "standalone"` for containerized/Vercel-compatible builds
- `postcss.config.mjs` — Tailwind CSS 4 via `@tailwindcss/postcss`
- `tsconfig.json` — Strict mode, `@/*` path alias mapped to `src/*`

**Dependencies** (`package.json`):
- `next@^15.1.0`, `react@^19.0.0`, `react-dom@^19.0.0`
- Dev: `typescript@^5.7.0`, `tailwindcss@^4.0.0`, `eslint-config-next`

**Dockerfile**: Three-stage Node 22 Alpine build (deps → build → standalone runner).

---

### Infrastructure

**Docker Compose** (`docker-compose.yml`):
- `db` — Postgres 16 Alpine with healthcheck, port 5432, named volume `pgdata`
- `backend` — FastAPI service on port 8000, depends on healthy db, dev volume mount for `app/`
- `frontend` — Next.js service on port 3000, no dependency on backend (independently deployable)

**Environment configuration:**
- `frontend/.env.local` — `NEXT_PUBLIC_API_URL` (gitignored)
- `backend/.env` — Database URLs, secret key, CORS origins (gitignored)
- Docker Compose sets env vars inline per service (overrides `.env` files with container-appropriate hostnames)

**Deployment model:**
- Frontend and backend are fully decoupled — communicate over HTTP via `NEXT_PUBLIC_API_URL`
- No API proxy/rewrite — frontend calls backend directly (CORS-configured)
- `CORS_ORIGINS` configurable on backend (defaults to `["http://localhost:3000"]`)
- Each service can be deployed independently (e.g., frontend → Vercel, backend → Fly.io, database → Supabase/RDS)

**`.gitignore`**: Python (`__pycache__`, `.venv`), Node (`node_modules`, `.next`), env files (`.env`, `.env.local`), IDE files, Docker volumes, Alembic migration files (keeps `.gitkeep`).

---

### Documentation

- `docs/vision.md` — Full SevenRooms product blueprint and feature reference (pre-existing)
- `docs/v1-blueprint.md` — Technical blueprint covering:
  - V1 scope (4 modules: Reservations, Table Mgmt, CRM, Surveys)
  - Tech stack and architecture decisions
  - Complete data model with field-level specifications
  - Module details with feature breakdowns and algorithms (e.g., availability engine)
  - 40+ API endpoint definitions
  - 4-phase development plan with exit criteria per phase
  - Non-functional requirements and open questions
