# Phase 2G — Booking Widget (Frontend): Completion Notes

**Date**: 2026-03-31
**Status**: Complete

---

## What Was Built

Phase 2G delivers the guest-facing booking widget — a public page where customers can find available times and book a table without any login.

---

## Booking Widget Page

**File**: `frontend/src/app/book/[venueId]/page.tsx`

**URL**: `/book/{venue_id}` — publicly accessible, no authentication.

### Multi-Step Flow

| Step | Screen | API Call |
|------|--------|----------|
| 1. **Date & Party Size** | Date picker + party size grid (1–10) | — |
| 2. **Time Slot Selection** | Slots grouped by meal period (access rule name), 3-column grid | `GET /venues/{id}/availability?date=...&party_size=...` |
| 3. **Guest Information** | First name, last name, email (required), phone, special requests textarea | — |
| 4. **Confirmation** | Summary review with Back/Confirm buttons | `POST /venues/{id}/reservations` |
| 5. **Success** | Green checkmark, booking details, "Make another reservation" link | — |

### Design

- **Mobile-first**: `max-w-md` centered card. On mobile devices (where most guest bookings happen), the card fills the viewport.
- **Touch-optimized**: Party size buttons in a 5-column grid, time slots in a 3-column grid. Large tap targets.
- **Venue branding**: Venue name and address displayed at the top, fetched from the public venue API on mount.
- **Clean, minimal**: White card on gray background. No navigation chrome — just the booking flow.

### Theming

Basic theming via URL query parameters:
- `?primaryColor=hex` — sets the primary button/selection color (default: `111827` / gray-900)
- Applied via inline `style` attribute so any hex value works without compile-time configuration
- Example: `/book/{venue_id}?primaryColor=2563eb` for blue

### API Integration

The widget uses a standalone `publicFetch` helper instead of the auth-injecting `api` client:
- No JWT token, no auth context needed
- Calls only two endpoints:
  1. `GET /venues/{id}/availability?date=...&party_size=...` — fetch available slots
  2. `POST /venues/{id}/reservations` — create reservation with `source: "widget"`

### Key Decisions

- **Email required for guests**: Unlike the staff booking form where email is optional, the widget requires email. This ensures the `get_or_create_guest()` service can deduplicate guest profiles.
- **`source: "widget"`**: All widget bookings are tagged with `source: "widget"`, distinct from `"admin"` (staff) and `"walk_in"` (waitlist). Enables booking channel analytics.
- **No auth context loaded**: The page doesn't import `AuthProvider` or `useAuth`. It's truly standalone — can be linked from any external website.
- **"Make another reservation"**: After success, guests can reset the form and book again without reloading the page.

---

## File Summary

### New files

```
frontend/src/app/book/[venueId]/page.tsx  — Public booking widget (5-step flow)
```

No modified files — the widget is entirely self-contained.

---

## Phase 2 — Complete

With Phase 2G, all seven sub-phases (2A through 2G) are complete. The full reservation flow works end-to-end:

1. Guest visits `/book/{venue_id}` → selects date/party/time → enters info → confirms
2. Backend validates availability, upserts guest profile, creates reservation
3. Staff sees the reservation in `/dashboard/reservations` → advances status through the lifecycle
4. Walk-ins are managed via the waitlist → can be seated and converted to reservations

### Phase 2 Exit Criteria Status

- [x] Access rules can be created and managed per venue via API
- [x] Availability engine returns correct open slots given date + party size
- [x] Reservations can be created, listed, and updated via API
- [x] Status machine enforces valid transitions
- [x] Cancellation sets `cancelled_at` and transitions to `cancelled` status
- [x] `completed` transition auto-creates a `GuestVisit` record
- [x] Waitlist entries can be added, listed, and status-updated via API
- [x] Guest profiles are auto-created/matched on reservation and waitlist creation
- [x] Staff can log in and see a daily reservation view in the frontend
- [x] Staff can advance reservation statuses from the UI
- [x] Staff can manage the waitlist from the UI
- [x] Guest can complete the booking widget flow
- [x] Booking widget creates a reservation and guest profile server-side
- [x] All endpoints return the standard API envelope format
- [x] Seed data script populates a usable demo environment
