# Pre-Phase 3 Quality Review — Completion

**Date**: 2026-03-31

Comprehensive code quality review and hardening pass across all Phase 2 code. Goal: reach 8.5+/10 production readiness before proceeding to Phase 3.

**20 findings addressed** across backend (10), frontend (5), and infrastructure (5).

---

## Backend Fixes

### 1. User Email Partial Unique Index (Critical → Fixed)

**Problem**: `User.email` had an unconditional `UNIQUE` constraint at the DB level, but the app used soft-deletes (`is_active=False`). After soft-deleting a user, their email was permanently blocked — new users couldn't register with it, contradicting the business logic that checks `is_active=True`.

**Fix**: Replaced global `UNIQUE` constraint with a PostgreSQL partial unique index (`WHERE is_active = true`). Only active users enforce email uniqueness; soft-deleted rows no longer block reuse.

**Files**:
- `backend/app/models/user.py` — `__table_args__` with partial index, removed `unique=True` from column
- `backend/alembic/versions/0003_quality_hardening.py` — Migration: drops old constraint, creates partial index

---

### 2. Database Connection Pooling (High → Fixed)

**Problem**: `create_async_engine()` used SQLAlchemy defaults (~5 connections). Under concurrent load, connection exhaustion would cascade into timeouts.

**Fix**: Added explicit pool configuration: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`.

**File**: `backend/app/core/database.py:8-12`

---

### 3. Cancel Token Index (High → Fixed)

**Problem**: `cancel_token` was `UNIQUE` but not explicitly indexed. Every public cancel request did a lookup on this column — without an index, this becomes a full table scan as reservations grow.

**Fix**: Added `index=True` to the `cancel_token` column definition. Migration adds the index.

**Files**:
- `backend/app/models/reservation.py:109-111`
- `backend/alembic/versions/0003_quality_hardening.py`

---

### 4. Access Rule Active Check on Reservation Create (High → Fixed)

**Problem**: `create_reservation` fetched the access rule by ID but didn't check `is_active=True` or `venue_id`. If an admin deactivated a rule between the availability check and booking, the deposit requirement would be silently skipped (defaulting to "confirmed" status).

**Fix**: Added `is_active=True` and `venue_id` filters to the access rule lookup. If the rule was deactivated, returns HTTP 409 "Access rule is no longer available" instead of silently proceeding.

**File**: `backend/app/services/reservation.py:135-145`

---

### 5. Pagination with selectinload (Medium → Fixed)

**Problem**: `list_reservations` used `joinedload` with `.offset()` and `.limit()`. SQL LIMIT is applied before relationship join expansion, potentially returning fewer rows than `per_page`. The duplicated filter logic between count and paginated queries was also a maintenance risk.

**Fix**:
- Replaced `joinedload` with `selectinload` for paginated queries (loads relationships in separate queries, so LIMIT works correctly)
- Extracted shared `_apply_filters()` closure to eliminate filter duplication between count and data queries

**File**: `backend/app/services/reservation.py:170-226`

---

### 6. Timezone Validation on Venue (Medium → Fixed)

**Problem**: Venue `timezone` field accepted any string. Invalid IANA identifiers (typos like "America/New_Yurk") would silently fall back to UTC in the availability engine, causing wrong booking cutoffs.

**Fix**: Added `field_validator` on both `VenueCreate` and `VenueUpdate` that validates against `zoneinfo.ZoneInfo()`. Invalid timezones now fail at schema validation with a clear error message.

**File**: `backend/app/schemas/venue.py`

---

### 7. Party Size Change Re-Validation (Medium → Fixed)

**Problem**: `PATCH /reservations/{id}` allowed changing `party_size` without checking whether the new size still fit within the slot's `max_covers_per_slot`. Staff could inflate a party from 2→20, violating capacity limits.

**Fix**: When `party_size` changes, the service now counts other active covers in the same slot (excluding the current reservation) and returns HTTP 409 if the new size would exceed capacity.

**File**: `backend/app/services/reservation.py:265-291`

---

### 8. Rate Limiting on Public Endpoints (Medium → Fixed)

**Problem**: No rate limiting on auth (`/login`, `/register`, `/refresh`), availability, or public reservation creation endpoints. Vulnerable to brute-force, enumeration, and DoS.

**Fix**: Added `slowapi` dependency and applied per-IP rate limits:
- `/auth/register` — 5/minute
- `/auth/login` — 10/minute
- `/auth/refresh` — 20/minute
- `/venues/{id}/availability` — 30/minute
- `POST /venues/{id}/reservations` — 10/minute

**Files**:
- `backend/requirements.txt` — Added `slowapi>=0.1.9,<0.2.0`
- `backend/app/main.py` — Limiter setup and `RateLimitExceeded` handler
- `backend/app/api/v1/auth.py` — `@limiter.limit()` decorators
- `backend/app/api/v1/availability.py` — `@limiter.limit()` decorator
- `backend/app/api/v1/reservations.py` — `@limiter.limit()` decorator

---

### 9. Health Check with DB Connectivity (Low → Fixed)

**Problem**: `/health` returned 200 even when Postgres was down. Docker healthchecks and load balancers couldn't distinguish "process alive" from "fully ready."

**Fix**: Added `/health/ready` endpoint that executes `SELECT 1` against the database. Returns 200 on success, 503 on failure. The original `/health` remains as a lightweight liveness probe. Docker Compose healthcheck updated to use `/health/ready`.

**Files**:
- `backend/app/main.py:78-96`
- `docker-compose.yml:32`

---

### 10. AccessRuleUpdate Partial Validation (Low → Fixed)

**Problem**: `PATCH /access-rules/{id}` with only `start_time` (no `end_time`) could make `start_time >= end_time` without triggering the schema validator, because it only checked when both were provided.

**Fix**: Moved cross-field validation to the service layer in `update_access_rule()`. Resolves effective values by merging update fields with existing DB values, then validates the pair. Returns HTTP 422 on violations.

**File**: `backend/app/services/access_rule.py:55-80`

---

## Frontend Fixes

### 11. Replace alert() with Inline Error (High → Fixed)

**Problem**: `handleStatusChange` in the waitlist page used `alert()` for error feedback — jarring browser dialog that breaks UX consistency.

**Fix**: Added `actionError` state. Errors now render inline in the existing red alert box alongside loading errors.

**File**: `frontend/src/app/dashboard/waitlist/page.tsx:50-58`

---

### 12. Type-Safe 204 Response Handling (High → Fixed)

**Problem**: 204 No Content responses used `null as unknown as T` — unsafe type coercion that could cause runtime errors when callers assumed data was non-null.

**Fix**: Return `{ data: null, meta: null, errors: null } as Envelope<T>` (still a cast, but now `delete` is explicitly typed as `request<null>` so callers know data is null). Changed `api.delete` signature to `(path: string) => request<null>(...)`.

**File**: `frontend/src/lib/api.ts:96,138`

---

### 13. Token Refresh Mutex (Medium → Fixed)

**Problem**: Multiple concurrent 401 responses could each trigger their own `/auth/refresh` call simultaneously, causing token desync (second refresh uses a stale refresh token).

**Fix**: Added a shared `_refreshPromise` singleton. The first 401 that triggers a refresh stores its promise; subsequent concurrent 401s reuse the same promise instead of making redundant refresh calls. Promise is cleared in a `finally` block.

**File**: `frontend/src/lib/api.ts:46-73`

---

### 14. Non-null Assertion Guard (Medium → Fixed)

**Problem**: `selectedSlot!.time` used a non-null assertion without a rendering guard. If state got out of sync (e.g., selectedSlot was null but step was "guest"), this would crash.

**Fix**: Changed `{step === "guest" && (` to `{step === "guest" && selectedSlot && (` and replaced `selectedSlot!.time` with `selectedSlot.time`.

**File**: `frontend/src/app/dashboard/reservations/new/page.tsx:189-203`

---

### 15. Error Boundary for Dashboard (Low → Fixed)

**Problem**: No React error boundary around dashboard content. A single component error in reservations or waitlist would crash the entire dashboard with a white screen.

**Fix**: Created `ErrorBoundary` class component with a "Try again" recovery button. Wrapped `{children}` in `DashboardShell` with `<ErrorBoundary>`.

**Files**:
- `frontend/src/components/ErrorBoundary.tsx` — New file
- `frontend/src/app/dashboard/layout.tsx:125`

---

## Infrastructure Fixes

### 16. Multi-Worker Uvicorn (High → Fixed)

**Problem**: Dockerfile ran a single Uvicorn worker. Production throughput was limited to one async event loop with no failover.

**Fix**: Added `--workers 4` to the Uvicorn CMD in the Dockerfile.

**File**: `backend/Dockerfile:30`

---

### 17. Tighter Dependency Version Ranges (Medium → Fixed)

**Problem**: Backend used `fastapi>=0.115.0,<1.0.0` and `pydantic>=2.0.0,<3.0.0` — allowing untested major bumps. Frontend used `^` caret (e.g., `next: ^15.1.0`), allowing any minor version.

**Fix**:
- Backend: Tightened all ranges (e.g., `fastapi>=0.115.0,<0.116.0`, `pydantic>=2.0.0,<2.11.0`)
- Frontend: Changed all `^` to `~` tilde (e.g., `next: ~15.1.0` — patch updates only)

**Files**:
- `backend/requirements.txt`
- `frontend/package.json`

---

### 18. Production Docker Compose (Medium → Fixed)

**Problem**: No production-specific Docker Compose configuration. Missing resource limits, restart policies, and secret management.

**Fix**: Created `docker-compose.prod.yml` overlay with:
- `restart: always` on all services
- CPU/memory limits and reservations
- Environment variables sourced from external `.env` (no inline defaults)
- Database port not exposed externally
- Readiness healthcheck (`/health/ready`)

**File**: `docker-compose.prod.yml` — New file

---

### 19. Seed Script Production Guard (Low → Fixed)

**Problem**: `scripts/seed.py` would happily run in production, creating demo accounts with password "password" and printing credentials to stdout.

**Fix**: Added `ENVIRONMENT` check at the top of `seed()`. If `settings.ENVIRONMENT == "production"`, the script prints an error and exits with code 1.

**File**: `backend/scripts/seed.py:31-35`

---

### 20. Environment Variable Template (Low → Fixed)

**Problem**: No `.env.example` documenting required production variables. Deployers had to read config.py to discover what's needed.

**Fix**: Created `backend/.env.example` with all required variables, comments, and a command for generating `SECRET_KEY`.

**File**: `backend/.env.example` — New file

---

## Files Changed

| Area | Files Modified | Files Created |
|------|---------------|---------------|
| Backend models | `models/user.py`, `models/reservation.py` | — |
| Backend core | `core/database.py` | — |
| Backend services | `services/reservation.py`, `services/access_rule.py` | — |
| Backend schemas | `schemas/venue.py`, `schemas/access_rule.py` | — |
| Backend API | `api/v1/auth.py`, `api/v1/availability.py`, `api/v1/reservations.py` | — |
| Backend app | `main.py` | — |
| Backend deps | `requirements.txt` | — |
| Backend infra | `Dockerfile`, `scripts/seed.py` | `alembic/versions/0003_quality_hardening.py`, `.env.example` |
| Frontend lib | `lib/api.ts` | — |
| Frontend pages | `dashboard/waitlist/page.tsx`, `dashboard/reservations/new/page.tsx`, `dashboard/layout.tsx` | `components/ErrorBoundary.tsx` |
| Frontend config | `package.json` | — |
| Infra | `docker-compose.yml` | `docker-compose.prod.yml` |

---

## Migration Required

After pulling these changes, apply the new migration:

```bash
cd backend
alembic upgrade head   # Applies 0003_quality_hardening
```

This migration:
1. Drops the global `UNIQUE` constraint on `users.email`
2. Creates a partial unique index `ix_users_email_active` (`WHERE is_active = true`)
3. Adds index `ix_reservations_cancel_token` on `reservations.cancel_token`
