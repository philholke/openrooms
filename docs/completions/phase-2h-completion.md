# Phase 2H Completion: Code Quality & Security Hardening

**Date**: 2026-03-31

Comprehensive review and hardening pass across all Phase 2 code (2A-2G). Fixes 22 issues spanning security, concurrency, validation, error handling, and accessibility.

---

## Critical Fixes (Security & Data Integrity)

### 1. IDOR on Public Cancel Endpoint
- **Before**: `POST /reservations/{id}/cancel` accepted any UUID with no verification — anyone could cancel any reservation by guessing the ID.
- **After**: Reservations now generate a `cancel_token` (cryptographically random, 32-byte URL-safe) on creation. The cancel endpoint requires `?token=<cancel_token>` as a query parameter. Returns 401 if missing, 404 if token doesn't match.
- **Files**: `models/reservation.py`, `services/reservation.py`, `api/v1/reservations.py`, `schemas/reservation.py`

### 2. Race Condition on Slot Availability
- **Before**: Two concurrent booking requests could both pass the availability check and exceed `max_covers_per_slot`.
- **After**: `create_reservation` now acquires a `SELECT FOR UPDATE` lock on existing reservations for the target venue+date before checking availability. This serialises concurrent inserts targeting the same slot.
- **Files**: `services/reservation.py`

### 3. Guest Upsert Race Condition
- **Before**: `get_or_create_guest` used a query-then-insert pattern. Concurrent requests with the same `(org_id, email)` could both find no match and attempt duplicate inserts, causing an unhandled `IntegrityError` (500).
- **After**: The `IntegrityError` is caught; on conflict, the transaction rolls back and re-fetches the winning row.
- **Files**: `services/guest.py`

---

## High-Priority Fixes

### 4. AccessRuleUpdate Missing Deposit Validation
- Added `require_deposit` / `deposit_amount_cents` cross-field validation to `AccessRuleUpdate` (was only in `AccessRuleCreate`).
- **Files**: `schemas/access_rule.py`

### 5. Frontend Token Refresh Mechanism
- **Before**: When the access token expired, users were silently logged out with no refresh attempt.
- **After**: The API client now intercepts 401 responses, attempts a single token refresh via `POST /auth/refresh`, and retries the original request. If refresh fails, clears tokens and redirects to `/login`.
- **Files**: `frontend/src/lib/api.ts`

### 6. Global 401 Error Handler
- Built into the API client (fix #5). Components no longer need individual 401 handling.
- **Files**: `frontend/src/lib/api.ts`

### 7. JSON Parse Safety in API Client
- **Before**: `res.json()` could throw `SyntaxError` on malformed responses, crashing the app.
- **After**: JSON parsing is wrapped in try-catch in both `apiFetch` and `publicFetch`, producing a clear `ApiError` / `Error` instead.
- **Files**: `frontend/src/lib/api.ts`, `frontend/src/app/book/[venueId]/page.tsx`

### 8. Null Type Safety for 204 Responses
- Changed `null as T` to `null as unknown as T` to avoid type assertion violations.
- **Files**: `frontend/src/lib/api.ts`

### 9. Timezone Fallback Logging
- **Before**: Invalid venue timezone silently fell back to UTC via bare `except Exception`.
- **After**: Logs a warning with the invalid timezone name and exception details before falling back.
- **Files**: `services/availability.py`

### 10. Pagination Tiebreaker
- Added `Reservation.id` as secondary sort to `list_reservations` to prevent non-deterministic pagination when multiple reservations share the same time.
- **Files**: `services/reservation.py`

---

## Medium-Priority Fixes

### 11. Status Transition Race Condition
- `update_status` now acquires a `SELECT FOR UPDATE` lock on the reservation row before reading status, preventing concurrent transitions from both passing validation.
- **Files**: `services/reservation.py`

### 12. Atomic Waitlist Seating
- **Before**: `seat_from_waitlist` flushed the waitlist status change before creating the reservation, risking an orphaned "seated" entry if the reservation insert failed.
- **After**: Single `flush()` after both the status change and reservation insert, keeping them atomic.
- **Files**: `services/waitlist.py`

### 13. Frontend Error State Display
- **Before**: Reservations page, waitlist page, and venue context silently swallowed errors and set data to empty arrays — indistinguishable from "no data".
- **After**: All three now capture error messages and display them in red alert banners. Venue context exposes an `error` field.
- **Files**: `frontend/src/app/dashboard/reservations/page.tsx`, `frontend/src/app/dashboard/waitlist/page.tsx`, `frontend/src/lib/venue.ts`

### 14. Auth Guard Race Condition
- **Before**: `!loading && !user` could briefly be true before the user context was set, causing a redirect flash.
- **After**: Loading and no-user states are handled separately. Uses `router.replace` (not `push`) and returns `null` while redirect is in flight to avoid visual flicker.
- **Files**: `frontend/src/app/dashboard/layout.tsx`

### 15. CSS Injection via primaryColor
- **Before**: URL parameter injected directly into inline `backgroundColor` style with no validation.
- **After**: Validates against `/^[0-9A-Fa-f]{3,8}$/` regex; falls back to default gray if invalid.
- **Files**: `frontend/src/app/book/[venueId]/page.tsx`

### 16. SPA Navigation Fix
- Replaced `window.location.href = "/dashboard/reservations/new"` with `router.push()` to preserve SPA state and avoid full page reloads.
- **Files**: `frontend/src/app/dashboard/reservations/page.tsx`

### 17. UUID Parse Error Handling
- **Before**: `uuid.UUID(user_id)` in `get_current_user` raised unhandled `ValueError` on malformed JWT subject, returning 500.
- **After**: Catches `ValueError` and returns 401 with "Invalid token subject".
- **Files**: `backend/app/core/dependencies.py`

---

## Low-Priority Fixes

### 18. String Length Validation in Schemas
- Added `Field(max_length=...)` constraints across all input schemas to match database column limits and return 422 instead of 500 on oversized strings.
- Added `Field(min_length=8)` to password fields for basic password strength.
- **Files**: `schemas/auth.py`, `schemas/user.py`, `schemas/venue.py`, `schemas/organization.py`, `schemas/guest.py`, `schemas/access_rule.py`

### 19. Missing Schemas for Future Modules
- Created `schemas/survey.py` with rating range validation (`ge=1, le=5`).
- Created `schemas/floor_plan.py` with capacity and label validation.
- Created `schemas/tag.py` with hex color format validation (`#RRGGBB`).
- **Files**: `schemas/survey.py`, `schemas/floor_plan.py`, `schemas/tag.py` (new files)

### 20. Missing API Endpoints
- Added `GET /access-rules/{rule_id}` for single-rule reads (manager+ auth).
- Added `DELETE /waitlist/{entry_id}` for cancelling waitlist entries (staff+ auth, soft delete via status change to "cancelled").
- **Files**: `api/v1/access_rules.py`, `api/v1/waitlist.py`

### 21. Accessibility Improvements
- Added `aria-label="Close"` to Modal close button.
- Added `tabIndex={0}`, `role="button"`, and `onKeyDown` handler (Enter/Space) to reservation table rows for keyboard navigation.
- **Files**: `frontend/src/components/ui/Modal.tsx`, `frontend/src/app/dashboard/reservations/page.tsx`

### 22. Pagination Size
- Reduced default `per_page` from 100 to 50 on the reservations page to limit memory usage for busy venues.
- **Files**: `frontend/src/app/dashboard/reservations/page.tsx`

---

## Auth Token Cleanup
- Centralised `clearTokens()` to also remove `selected_venue_id` from localStorage on logout/auth failure, preventing stale venue preferences leaking across sessions.
- Removed duplicate `React` import in `auth.ts`.
- **Files**: `frontend/src/lib/auth.ts`, `frontend/src/lib/api.ts`

---

## Files Modified

### Backend (13 files)
- `app/models/reservation.py` — added `cancel_token` column
- `app/services/reservation.py` — SELECT FOR UPDATE locks, cancel_token generation, pagination tiebreaker
- `app/services/guest.py` — IntegrityError handling for concurrent upsert
- `app/services/availability.py` — timezone warning logging
- `app/services/waitlist.py` — atomic flush for seat_from_waitlist
- `app/core/dependencies.py` — UUID parse error handling
- `app/api/v1/reservations.py` — cancel token verification
- `app/api/v1/access_rules.py` — GET single endpoint
- `app/api/v1/waitlist.py` — DELETE endpoint
- `app/schemas/` — max_length, min_length, deposit validation across 7 existing files
- `app/schemas/survey.py` — new
- `app/schemas/floor_plan.py` — new
- `app/schemas/tag.py` — new

### Frontend (8 files)
- `src/lib/api.ts` — token refresh, 401 handler, JSON parse safety
- `src/lib/auth.ts` — centralised clearTokens, removed duplicate import
- `src/lib/venue.ts` — error state
- `src/app/dashboard/layout.tsx` — auth guard race fix
- `src/app/dashboard/reservations/page.tsx` — error display, SPA nav, keyboard access
- `src/app/dashboard/waitlist/page.tsx` — error display
- `src/app/book/[venueId]/page.tsx` — color validation, JSON parse safety
- `src/components/ui/Modal.tsx` — aria-label

---

## Migration Note

The `cancel_token` column added to the `reservations` table requires a new Alembic migration before deployment:
```bash
cd backend
alembic revision --autogenerate -m "add_cancel_token_to_reservations"
alembic upgrade head
```
