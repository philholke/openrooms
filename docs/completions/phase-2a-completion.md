# Phase 2A — Backend Foundation: Completion Notes

**Date**: 2026-03-31
**Status**: Complete

---

## What Was Built

Phase 2A delivers the shared infrastructure that all subsequent Phase 2 endpoints depend on: the API response envelope, JWT authentication, and Org/Venue/User CRUD.

---

## Task 2A.1 — API Response Envelope

**File**: `backend/app/schemas/envelope.py`

Created a generic response wrapper for consistent API responses:

| Export | Purpose |
|--------|---------|
| `Envelope[T]` | Generic Pydantic model wrapping a single `data` item, optional `meta` and `errors` |
| `PaginatedEnvelope[T]` | Same but `data` is `list[T]` and `meta` is required |
| `ErrorDetail` | Schema with `field`, `message`, `code` for structured error responses |
| `Meta` | Pagination metadata: `page`, `per_page`, `total` |
| `ok(data)` | Helper — wraps data in envelope dict |
| `paginated(data, page, per_page, total)` | Helper — wraps list with pagination meta |
| `error(errors)` | Helper — wraps error details |

**Design decision**: Helpers return plain dicts instead of model instances. FastAPI's `response_model` handles final serialization, so we avoid the overhead of constructing a Pydantic model just to serialize it again.

---

## Task 2A.2 — Auth & JWT Middleware

### `backend/app/core/security.py`

| Function | Purpose |
|----------|---------|
| `hash_password(password)` | bcrypt hash via passlib |
| `verify_password(plain, hashed)` | bcrypt verify |
| `create_access_token(subject, extra?)` | JWT with `type: "access"`, configurable expiry from settings |
| `create_refresh_token(subject)` | JWT with `type: "refresh"`, 7-day expiry |
| `verify_token(token, expected_type)` | Decode + validate; returns payload dict or `None` |

**Key detail**: The `type` claim in the JWT payload (`access` vs `refresh`) prevents token misuse — a refresh token can't be used as a Bearer token on protected endpoints.

### `backend/app/core/dependencies.py`

| Dependency | Purpose |
|------------|---------|
| `get_current_user` | Extracts JWT from `Authorization: Bearer` header, loads active User from DB |
| `get_current_org` | Derives Organization from the current user's `org_id` |
| `require_role(min_role)` | Factory returning a dependency that checks role hierarchy |

**Role hierarchy**: `owner(0) > admin(1) > manager(2) > staff(3)`. `require_role("manager")` allows owner, admin, and manager.

### `backend/app/api/v1/auth.py`

| Endpoint | Method | Path | Description |
|----------|--------|------|-------------|
| Register | POST | `/api/v1/auth/register` | Creates Organization + owner User atomically, returns JWT pair |
| Login | POST | `/api/v1/auth/login` | Email + password → JWT pair |
| Refresh | POST | `/api/v1/auth/refresh` | Refresh token → new token pair |

### `backend/app/schemas/auth.py`

Schemas: `RegisterRequest`, `LoginRequest`, `RefreshRequest`, `TokenResponse`.

**Dependency added**: `email-validator>=2.0.0` in `requirements.txt` (required by Pydantic's `EmailStr`).

---

## Task 2A.3 — Org, Venue, and User CRUD

### Schemas

| File | Schemas |
|------|---------|
| `backend/app/schemas/organization.py` | `OrgUpdate`, `OrgRead` |
| `backend/app/schemas/venue.py` | `VenueCreate`, `VenueUpdate`, `VenueRead` |
| `backend/app/schemas/user.py` | `UserCreate`, `UserUpdate`, `UserRead` |

All `*Read` schemas use `model_config = {"from_attributes": True}` for direct SQLAlchemy model → Pydantic conversion.

`UserCreate.role` is `Literal["admin", "manager", "staff"]` — owner role can only be assigned during registration, preventing privilege escalation via the user CRUD API. `UserUpdate.role` allows all four roles but the endpoint guards `owner` assignment to owner-only.

### API Endpoints

**Organization** (`backend/app/api/v1/organizations.py`):

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/org` | any authenticated | Get current org |
| PATCH | `/api/v1/org` | admin+ | Update org name/slug |

**Venues** (`backend/app/api/v1/venues.py`):

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/venues` | staff+ | List venues (paginated) |
| POST | `/api/v1/venues` | admin+ | Create venue |
| GET | `/api/v1/venues/{id}` | staff+ | Get single venue |
| PATCH | `/api/v1/venues/{id}` | manager+ | Update venue |
| DELETE | `/api/v1/venues/{id}` | admin+ | Soft-delete venue |

**Users** (`backend/app/api/v1/users.py`):

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/users/me` | any authenticated | Get current user |
| GET | `/api/v1/users` | admin+ | List users (paginated) |
| POST | `/api/v1/users` | admin+ | Create user |
| GET | `/api/v1/users/{id}` | admin+ | Get single user |
| PATCH | `/api/v1/users/{id}` | admin+ | Update user |
| DELETE | `/api/v1/users/{id}` | admin+ | Soft-delete user |

**Router** (`backend/app/api/v1/router.py`): Updated to include `auth`, `org`, `venues`, and `users` sub-routers.

### Multi-tenancy enforcement

Every query includes an `org_id` filter derived from the authenticated user's organization. All list endpoints are paginated via `?page=N&per_page=N` with the standard meta envelope.

---

## Task 2A.4 — Alembic Initial Migration

**File**: `backend/alembic/versions/0001_initial_schema.py`

Hand-written migration covering all 12 entities (13 tables including the `guest_tags` association table). Written by hand rather than auto-generated so it works without a running database.

Tables are created in FK-dependency order:
1. `organizations` (root)
2. `users`, `venues`, `tags`, `guest_profiles` (FK → organizations)
3. `guest_tags` (FK → guest_profiles, tags)
4. `floor_plans` (FK → venues)
5. `tables` (FK → floor_plans)
6. `access_rules` (FK → venues)
7. `reservations` (FK → venues, guest_profiles, tables, access_rules) + composite index on `(venue_id, date)`
8. `waitlist_entries` (FK → venues, guest_profiles)
9. `guest_visits` (FK → guest_profiles, venues, reservations)
10. `surveys` (FK → venues, reservations, guest_profiles)

`downgrade()` drops in reverse order.

**To apply**: `cd backend && alembic upgrade head` (requires running Postgres).

---

## Task 2A.5 — Seed Data Script

**File**: `backend/scripts/seed.py`

Run via: `cd backend && python -m scripts.seed`

Creates:
- **1 Organization**: "Demo Restaurant Group" (slug: `demo`)
- **3 Users**: `owner@demo.com`, `manager@demo.com`, `staff@demo.com` (password: `password` for all)
- **2 Venues**: "Downtown Bistro" (10 tables) and "Waterfront Grill" (12 tables)
- **1 Floor plan per venue** with tables across varied sections (Window, Main, Private, Bar, Deck, Interior, Private Dining)
- **3 Access rules per venue**: Lunch (Mon-Fri 11:30-14:00), Dinner (daily 17:30-21:30), Weekend Brunch (Sat-Sun 10:00-14:00)
- **8 Guest profiles** with varied data (dietary restrictions, birthdays, anniversaries, notes)

The script is **idempotent** — checks for existing `demo` slug before inserting.

---

## File Summary

### New files created

```
backend/app/schemas/envelope.py       — API envelope + helpers
backend/app/schemas/auth.py           — Auth request/response schemas
backend/app/schemas/organization.py   — Org schemas
backend/app/schemas/venue.py          — Venue schemas
backend/app/schemas/user.py           — User schemas
backend/app/core/security.py          — JWT + password hashing
backend/app/core/dependencies.py      — Auth dependencies + role guard
backend/app/api/v1/auth.py            — Register/login/refresh endpoints
backend/app/api/v1/organizations.py   — Org GET/PATCH
backend/app/api/v1/venues.py          — Venue CRUD
backend/app/api/v1/users.py           — User CRUD
backend/alembic/versions/0001_initial_schema.py — Initial migration (all 12 entities)
backend/scripts/__init__.py           — Package marker
backend/scripts/seed.py               — Demo data seeder
```

### Modified files

```
backend/app/api/v1/router.py          — Wired up auth, org, venues, users sub-routers
backend/requirements.txt              — Added email-validator>=2.0.0
```
