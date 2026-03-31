# Phase 2F — Staff Reservation View (Frontend): Completion Notes

**Date**: 2026-03-31
**Status**: Complete

---

## What Was Built

Phase 2F delivers the staff-facing dashboard: auth pages, sidebar layout with venue selector, reservation list with status management, staff booking form, and waitlist management.

---

## Task 2F.1 — Frontend Project Setup

### Lib Layer

| File | Purpose |
|------|---------|
| `src/lib/types.ts` | TypeScript interfaces mirroring all backend schemas (Envelope, User, Venue, Reservation, WaitlistEntry, etc.) |
| `src/lib/api.ts` | Fetch-based API client with auto auth token injection, envelope parsing, `ApiError` class |
| `src/lib/utils.ts` | `formatTime`, `formatDate`, `formatDateTime`, `today`, `minutesElapsed`, `cn` (class merge) |

### UI Primitives (`src/components/ui/`)

| Component | Features |
|-----------|----------|
| `Button` | 4 variants (primary/secondary/danger/ghost), 3 sizes, disabled state |
| `Input` | Label, error display, full HTML input pass-through |
| `Select` | Label, options array, HTML select pass-through |
| `Badge` | Color variants + `StatusBadge` mapping reservation/waitlist statuses to colors |
| `Modal` | Overlay + escape key + click-outside close |
| `Card` | Bordered container with optional click handler |

All built with Tailwind CSS — no component library dependency.

---

## Task 2F.2 — Auth Pages

| File | Purpose |
|------|---------|
| `src/lib/auth.ts` | `AuthProvider` context, `useAuth()` hook — login/register/logout, token storage in localStorage, auto-fetch user on mount |
| `src/app/providers.tsx` | Client-side providers wrapper (AuthProvider) |
| `src/app/layout.tsx` | Updated to wrap with `<Providers>` |
| `src/app/login/page.tsx` | Login form → JWT → redirect to dashboard |
| `src/app/register/page.tsx` | Register form with auto-slug generation from org name |

Token storage: `localStorage` (simple for V1; httpOnly cookie is a production hardening step).

---

## Task 2F.3 — Dashboard Layout

| File | Purpose |
|------|---------|
| `src/lib/venue.ts` | `VenueProvider` context, `useVenue()` hook — loads venues, persists selected venue to localStorage |
| `src/app/dashboard/layout.tsx` | Sidebar (nav links, venue selector), top bar (user name, sign out), auth guard redirect |
| `src/app/dashboard/page.tsx` | Redirects to `/dashboard/reservations` |

**Layout**: Fixed 224px sidebar + 56px top bar. Content area at `ml-56 pt-14`. Sidebar shows: Reservations, Waitlist nav links + venue selector for multi-venue orgs.

**Auth guard**: Dashboard layout checks `useAuth()` — redirects unauthenticated users to `/login`.

---

## Task 2F.4 + 2F.5 — Reservations List + Detail

### Reservations List (`src/app/dashboard/reservations/page.tsx`)

- Date picker (defaults to today)
- Status filter tabs: All | Upcoming | Seated | Completed | Cancelled
- Table view: time, guest name, party size, table assignment, status badge, notes
- Click row → opens detail modal
- "New Reservation" button → navigates to `/dashboard/reservations/new`
- 30-second auto-refresh + manual refresh button
- Total count display

### Reservation Detail (`src/components/reservations/ReservationDetail.tsx`)

- Modal showing: guest info (name, email, phone, dietary restrictions), booking details (date, time, party size, table, access rule), special requests, notes
- **Contextual status actions** based on current status:
  - `pending` → Confirm, Cancel
  - `confirmed` → Mark Arrived, No Show, Cancel
  - `arrived` / `partially_arrived` → Seat, No Show
  - `seated` → Complete
- Actions call backend status/cancel endpoints and refresh the list

---

## Task 2F.6 — Create Reservation Form

**File**: `src/app/dashboard/reservations/new/page.tsx`

4-step flow (all in one page, no URL routing between steps):

1. **Date & Party Size** — date picker + party size grid (1–12 buttons)
2. **Time Slot Selection** — calls availability API, groups slots by access rule name (meal period)
3. **Guest Information** — first/last name, email, phone, special requests
4. **Confirmation** — summary review → submit

On success, redirects to reservation list.

---

## Task 2F.7 — Waitlist View

**File**: `src/app/dashboard/waitlist/page.tsx`

- Card-based active waitlist (FIFO order)
- Each card: party size circle, guest name, elapsed wait / quoted wait, phone, status badge
- Inline action buttons:
  - `waiting` → Notify, Seat, No Show
  - `notified` → Seat, No Show
- "Add to Waitlist" modal: first/last name, phone, party size (1–10 buttons), quoted wait, notes
- 15-second auto-refresh (faster than reservation list — waitlist changes quickly during service)

---

## File Summary

### New files (20 files)

```
src/lib/types.ts                                  — TypeScript type definitions
src/lib/api.ts                                    — API client
src/lib/utils.ts                                  — Formatting helpers
src/lib/auth.ts                                   — Auth context + provider
src/lib/venue.ts                                  — Venue context + provider
src/app/providers.tsx                              — Client providers wrapper
src/app/login/page.tsx                             — Login page
src/app/register/page.tsx                          — Register page
src/app/dashboard/layout.tsx                       — Dashboard shell (sidebar, top bar, auth guard)
src/app/dashboard/page.tsx                         — Redirects to /reservations
src/app/dashboard/reservations/page.tsx            — Reservation list view
src/app/dashboard/reservations/new/page.tsx        — Staff booking form (4-step)
src/app/dashboard/waitlist/page.tsx                — Waitlist management view
src/components/ui/Button.tsx                       — Button component
src/components/ui/Input.tsx                        — Input component
src/components/ui/Select.tsx                       — Select component
src/components/ui/Badge.tsx                        — Badge + StatusBadge components
src/components/ui/Modal.tsx                        — Modal component
src/components/ui/Card.tsx                         — Card component
src/components/reservations/ReservationDetail.tsx  — Reservation detail modal
```

### Modified files

```
src/app/layout.tsx                                 — Wrapped with Providers
```
