# OpenRooms V1 Blueprint

Open-source SevenRooms clone. Target >80% of core reservation operations functionality. No commercial fluff.

---

## V1 Scope

Four modules only:

| # | Module | Summary |
|---|--------|---------|
| 1 | Reservations & Waitlist | Booking widget, access rules, availability engine, deposits/cancellation policies, virtual waitlist, SMS/email confirmations (future) |
| 2 | Table Management | Interactive floor plan, drag-and-drop seating, server assignment, pacing, pre-shift reports, table statuses |
| 3 | CRM & Guest Profiles | Auto-built profiles from every touchpoint, 100+ data points, manual tags, auto-tags with rule engine, segmentation |
| 4 | Post-Visit Surveys | Automated post-visit feedback collection, multi-dimension ratings, comment capture, linked to guest profile |

### Explicitly Out of Scope for V1

Marketing Automation, Events/Experiences, Online Ordering, Loyalty/VIP/Retention, AI Features, external integrations (POS, Twilio, Stripe, Google/Facebook booking channels), review aggregation from third-party platforms, advanced reporting.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (App Router, TypeScript, Tailwind CSS) |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL (portable -- runs on Supabase, AWS RDS, Fly.io, self-hosted) |
| ORM | SQLAlchemy 2.0 (async with asyncpg) |
| Migrations | Alembic |
| Containerization | Docker + docker-compose for local dev |

---

## Architecture

### Multi-Tenancy

- Tenant boundary: **Organization** (not Venue).
- An Organization can have 1 or many Venues.
- Guest profiles are org-scoped (shared across venues within an org).
- A single restaurant is just an org with one venue -- no special case.
- User permissions are per-org with optional per-venue granularity.

### Entity Hierarchy

```
Organization (tenant root)
├── Users (staff with org-level roles: owner, admin, manager, staff)
├── Guest Profiles (shared across all venues in the org)
│   ├── Tags (many-to-many)
│   ├── Visits (per-venue history)
│   └── Surveys
├── Tags (org-scoped, manual + auto-tags)
└── Venues
    ├── Floor Plans → Tables
    ├── Access Rules (availability, pacing, policies)
    ├── Reservations (linked to guest, table, access rule)
    ├── Waitlist Entries
    └── Surveys (linked to guest + reservation)
```

### API Design

- RESTful API at `/api/v1/`.
- All responses use a consistent envelope format:
  ```json
  {
    "data": { ... },
    "meta": { "page": 1, "per_page": 25, "total": 142 },
    "errors": null
  }
  ```
- UUID primary keys throughout.
- Cursor-based or offset pagination on all list endpoints.
- OpenAPI docs auto-generated at `/docs`.
- Auth via JWT tokens (short-lived access + refresh).

---

## Data Model

### Organization

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| name | string | not null |
| slug | string | unique, not null |
| is_active | boolean | default true |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

### User

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| org_id | UUID | FK → Organization, not null |
| email | string | unique, not null |
| hashed_password | string | not null |
| full_name | string | not null |
| role | enum | owner / admin / manager / staff, not null |
| is_active | boolean | default true |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

Roles define coarse access control:

| Role | Scope |
|------|-------|
| owner | Full org access, billing, can delete org |
| admin | Full operational access across all venues |
| manager | Operational access, scoped to assigned venues |
| staff | Read-only + limited write (seat guests, update statuses) |

### Venue

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| org_id | UUID | FK → Organization, not null |
| name | string | not null |
| slug | string | unique within org |
| address | string | nullable |
| timezone | string | not null (e.g., `America/New_York`) |
| phone | string | nullable |
| email | string | nullable |
| is_active | boolean | default true |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

Unique constraint on `(org_id, slug)`.

### GuestProfile

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| org_id | UUID | FK → Organization, not null |
| first_name | string | nullable |
| last_name | string | nullable |
| email | string | nullable |
| phone | string | nullable |
| birthday | date | nullable |
| anniversary | date | nullable |
| dietary_restrictions | string | nullable |
| notes | text | nullable |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

Unique constraint on `(org_id, email)` where email is not null (partial unique index).

Profiles are created automatically from any touchpoint: reservation, waitlist entry, or survey. Deduplication uses the `(org_id, email)` constraint -- if an incoming reservation matches an existing profile by org + email, the existing profile is reused and enriched.

### Tag

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| org_id | UUID | FK → Organization, not null |
| name | string | not null |
| color | string | hex, nullable (e.g., `#FF5733`) |
| is_auto | boolean | default false |
| description | string | nullable |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

Unique constraint on `(org_id, name)`.

Manual tags (`is_auto = false`) are applied by staff. Auto-tags (`is_auto = true`) are applied by the rule engine based on conditions (see Module 3).

### GuestTag

Association table (many-to-many between GuestProfile and Tag).

| Field | Type | Constraints |
|-------|------|-------------|
| guest_id | UUID | FK → GuestProfile, PK |
| tag_id | UUID | FK → Tag, PK |
| created_at | timestamptz | not null |

### GuestVisit

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| guest_id | UUID | FK → GuestProfile, not null |
| venue_id | UUID | FK → Venue, not null |
| reservation_id | UUID | FK → Reservation, nullable |
| visited_at | timestamptz | not null |
| spend_amount | integer | nullable, cents (for future POS integration) |
| notes | text | nullable |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

A visit is created when a reservation reaches `completed` status, or can be created manually for walk-ins.

### FloorPlan

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| venue_id | UUID | FK → Venue, not null |
| name | string | not null (e.g., "Main Dining", "Patio", "Bar") |
| is_active | boolean | default true |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

### Table

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| floor_plan_id | UUID | FK → FloorPlan, not null |
| label | string | not null (e.g., "T1", "Bar 3", "Patio 12") |
| min_capacity | integer | not null |
| max_capacity | integer | not null |
| section | string | nullable (used for server assignment grouping) |
| x_position | float | not null (canvas coordinate) |
| y_position | float | not null (canvas coordinate) |
| shape | enum | rectangle / circle / square, default rectangle |
| is_active | boolean | default true |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

### AccessRule

Access rules define when and how reservations can be made. They are the core of the availability engine.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| venue_id | UUID | FK → Venue, not null |
| name | string | not null (e.g., "Dinner Service", "Brunch Weekend") |
| days_of_week | integer[] | not null (0=Mon ... 6=Sun) |
| start_date | date | nullable (null = no start bound) |
| end_date | date | nullable (null = no end bound) |
| start_time | time | not null |
| end_time | time | not null |
| slot_interval_minutes | integer | not null (e.g., 15, 30) |
| min_party_size | integer | not null, default 1 |
| max_party_size | integer | not null |
| max_covers_per_slot | integer | nullable (null = unlimited) |
| advance_booking_days | integer | not null (how far ahead guests can book) |
| cutoff_minutes | integer | not null (stop accepting bookings X min before slot) |
| require_deposit | boolean | default false |
| deposit_amount_cents | integer | nullable |
| cancellation_policy_hours | integer | nullable (cancel free before X hours) |
| cancellation_fee_cents | integer | nullable |
| seating_areas | string[] | nullable (restrict to specific floor plans/sections) |
| is_active | boolean | default true |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

**Availability calculation**: For a given date/time/party_size, the engine finds all active access rules that match, then checks `max_covers_per_slot` against existing confirmed reservations in that slot. Available slots are returned to the booking widget.

### Reservation

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| venue_id | UUID | FK → Venue, not null |
| guest_id | UUID | FK → GuestProfile, not null |
| table_id | UUID | FK → Table, nullable |
| access_rule_id | UUID | FK → AccessRule, nullable |
| party_size | integer | not null |
| date | date | not null |
| time | time | not null |
| status | enum | see below |
| source | string | nullable (widget / phone / walk-in / manual) |
| notes | text | nullable (internal staff notes) |
| special_requests | text | nullable (guest-facing) |
| cancelled_at | timestamptz | nullable |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

Index on `(venue_id, date)` for fast daily lookups.

**Reservation statuses and transitions:**

```
pending → confirmed → arrived → seated → completed
                   ↘ partially_arrived → seated → completed
pending → cancelled
confirmed → cancelled
confirmed → no_show
```

| Status | Meaning |
|--------|---------|
| pending | Created, awaiting confirmation (e.g., deposit required) |
| confirmed | Confirmed and expected |
| arrived | Guest has arrived, waiting to be seated |
| partially_arrived | Some of the party has arrived |
| seated | Guest is at their table |
| completed | Meal finished, table cleared |
| no_show | Guest did not show up |
| cancelled | Cancelled by guest or staff |

### WaitlistEntry

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| venue_id | UUID | FK → Venue, not null |
| guest_id | UUID | FK → GuestProfile, not null |
| party_size | integer | not null |
| estimated_wait_minutes | integer | nullable (system-calculated) |
| quoted_wait_minutes | integer | nullable (what the host told the guest) |
| status | enum | waiting / notified / seated / cancelled / no_show |
| check_in_time | timestamptz | not null |
| seated_time | timestamptz | nullable |
| notes | text | nullable |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

### Survey

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK |
| venue_id | UUID | FK → Venue, not null |
| reservation_id | UUID | FK → Reservation, nullable |
| guest_id | UUID | FK → GuestProfile, not null |
| overall_rating | integer | 1-5, not null |
| food_rating | integer | 1-5, nullable |
| service_rating | integer | 1-5, nullable |
| ambiance_rating | integer | 1-5, nullable |
| drinks_rating | integer | 1-5, nullable |
| comment | text | nullable |
| created_at | timestamptz | not null |
| updated_at | timestamptz | not null |

---

## Module Details

### Module 1: Reservations & Waitlist

**Booking Widget**

An embeddable, white-label widget that restaurants place on their website. Renders as an iframe or web component. The widget:

- Accepts `venue_id` as a parameter.
- Calls the availability API to fetch open slots for a selected date and party size.
- Collects guest info (name, email, phone, special requests).
- Creates or matches a GuestProfile, then creates a Reservation.
- Displays confirmation with reservation details.
- Styled with Tailwind; host site can pass a theme config (primary color, font) via URL params or embed attributes.

**Access Rules Engine**

The availability calculation is the core algorithm:

1. Receive query: `(venue_id, date, party_size)`.
2. Find all active AccessRules where:
   - `days_of_week` includes the target day.
   - `start_date <= date <= end_date` (or bounds are null).
   - `min_party_size <= party_size <= max_party_size`.
   - `advance_booking_days` allows the date.
3. For each matching rule, generate time slots from `start_time` to `end_time` at `slot_interval_minutes`.
4. For each slot, count existing confirmed/pending reservations. Exclude slots where covers >= `max_covers_per_slot`.
5. Exclude slots within `cutoff_minutes` of current time.
6. Return available slots grouped by access rule.

**Reservation Lifecycle**

```
Guest books via widget or staff creates manually
  → Reservation created (status: pending or confirmed)
  → If deposit required: status stays pending until deposit collected (future)
  → Day of: staff marks arrived / partially_arrived
  → Staff assigns table, marks seated
  → Meal completes: staff marks completed → GuestVisit auto-created
  → If no-show: staff marks no_show after configurable grace period
```

**Cancellation Policies**

Schema supports `cancellation_policy_hours` and `cancellation_fee_cents` on access rules. V1 stores the policy and displays it to the guest. Actual payment collection requires Stripe integration (out of scope). When a guest cancels:

- If within policy window: `cancelled_at` is set, status becomes `cancelled`.
- If outside policy window: same state change, but the cancellation fee is flagged for manual collection.

**Virtual Waitlist**

- Host adds walk-in guest to waitlist with party size and quoted wait.
- System tracks position and estimates wait time based on current table turn times.
- Waitlist entries can be promoted to reservations or seated directly.
- Status flow: `waiting → notified → seated` (or `cancelled` / `no_show`).

### Module 2: Table Management

**Floor Plan Editor**

- Canvas-based editor (HTML5 Canvas or SVG via React component).
- Drag-and-drop placement of tables.
- Each table has a label, capacity range, shape, and section.
- Multiple floor plans per venue (e.g., "Main Floor", "Patio", "Private Room", "Bar").
- Only one floor plan needs to be active at a time for the live seating view, but all can be edited.

**Table Statuses**

| Status | Meaning | Color (suggested) |
|--------|---------|--------------------|
| available | Empty, ready for seating | Green |
| occupied | Guest currently seated | Red |
| reserved | Held for an upcoming reservation | Blue |
| held | Temporarily blocked by staff | Yellow |

Table status is derived, not stored as a column. It is computed from:
- Current reservations assigned to the table with status `seated` → occupied.
- Upcoming reservations within the next N minutes → reserved.
- Manual hold flag → held.
- Otherwise → available.

**Server Section Assignment**

- Tables belong to sections (string field on Table).
- Staff view shows which server is assigned to which section (stored as a lightweight per-shift assignment, not a permanent model in V1 -- can use a simple key-value or a `ServerAssignment` table with `venue_id, date, section, user_id`).

**Pacing Visualization**

A bar chart or grid view showing:
- X-axis: time slots (e.g., every 15 minutes from 17:00 to 22:00).
- Y-axis: cover count.
- Each bar shows confirmed covers for that slot vs. the max_covers_per_slot from access rules.
- Helps managers see when the venue is overloaded and when there is room.

**Pre-Shift Report**

Auto-generated report for the upcoming shift, containing:
- Total covers expected.
- List of reservations with guest name, party size, time, table assignment, special requests.
- VIP or tagged guests highlighted.
- Notes and dietary restrictions surfaced.
- Exportable as PDF or printable HTML.

### Module 3: CRM & Guest Profiles

**Auto-Profile Creation**

A GuestProfile is created or matched on every touchpoint:
- Reservation created (via widget or manual).
- Waitlist entry created.
- Survey submitted.

Matching logic: look up by `(org_id, email)`. If found, reuse and enrich. If not found (or no email), create new. Phone-based dedup is a future enhancement.

**Tag System**

Two types of tags:

| Type | Created By | Applied By |
|------|-----------|------------|
| Manual | Staff | Staff (drag onto profile or bulk-apply) |
| Auto | Rule engine | System (on trigger) |

Auto-tag rules are stored as JSON conditions. Example rule:

```json
{
  "name": "Frequent Diner",
  "tag_id": "uuid-of-frequent-diner-tag",
  "conditions": {
    "visit_count": { "gte": 5 },
    "venue_id": null
  }
}
```

V1 supports simple conditions: `visit_count`, `last_visit_within_days`, `total_spend_gte`, `has_tag`, `average_rating_gte`. The rule engine runs on a schedule (cron) and on reservation completion.

**Guest Segmentation**

List view of all guests in the org with filters:

| Filter | Type |
|--------|------|
| Tags (include/exclude) | Multi-select |
| Visit count | Range (min/max) |
| Last visit date | Date range |
| Total spend | Range |
| Venue | Multi-select |
| Average survey rating | Range |
| Birthday month | Select |

Results are paginated and sortable. Future: export to CSV.

**Visit History Timeline**

Each guest profile page shows a chronological timeline:
- Reservations (with venue, date, party size, status).
- Waitlist entries.
- Survey responses.
- Tags added/removed.
- Notes added by staff.

### Module 4: Post-Visit Surveys

**Survey Configuration**

Each venue has a default survey template. V1 ships with one fixed template (the five rating dimensions + comment). Future versions can support custom questions.

**Survey Trigger**

When a reservation status changes to `completed`:
1. System queues a survey dispatch (stored in a `SurveyDispatch` table or handled via background task).
2. In V1, this generates a unique survey link. Actual email/SMS delivery is out of scope (requires Twilio/SendGrid integration). The link is available in the staff UI for manual sharing.
3. Guest opens link, submits ratings and comment.
4. Survey is linked to the guest profile and reservation.

**Rating Dimensions**

| Dimension | Required |
|-----------|----------|
| Overall | Yes |
| Food | No |
| Service | No |
| Ambiance | No |
| Drinks | No |

All ratings are 1-5 integers.

**Survey Dashboard**

Per-venue dashboard showing:
- Average ratings over time (line chart).
- Rating distribution (bar chart).
- Recent comments (with guest name and reservation date).
- Filter by date range and rating threshold.

---

## API Endpoints

### Organizations & Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new org + owner user |
| POST | `/api/v1/auth/login` | Login, returns JWT |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/org` | Get current org details |
| PATCH | `/api/v1/org` | Update org |

### Users

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users` | List users in org |
| POST | `/api/v1/users` | Invite/create user |
| GET | `/api/v1/users/{id}` | Get user |
| PATCH | `/api/v1/users/{id}` | Update user |
| DELETE | `/api/v1/users/{id}` | Deactivate user |

### Venues

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/venues` | List venues in org |
| POST | `/api/v1/venues` | Create venue |
| GET | `/api/v1/venues/{id}` | Get venue |
| PATCH | `/api/v1/venues/{id}` | Update venue |
| DELETE | `/api/v1/venues/{id}` | Deactivate venue |

### Floor Plans & Tables

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/floor-plans` | List floor plans |
| POST | `/api/v1/venues/{venue_id}/floor-plans` | Create floor plan |
| PATCH | `/api/v1/floor-plans/{id}` | Update floor plan |
| DELETE | `/api/v1/floor-plans/{id}` | Deactivate floor plan |
| GET | `/api/v1/floor-plans/{id}/tables` | List tables |
| POST | `/api/v1/floor-plans/{id}/tables` | Create table |
| PATCH | `/api/v1/tables/{id}` | Update table |
| DELETE | `/api/v1/tables/{id}` | Deactivate table |

### Access Rules

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/access-rules` | List access rules |
| POST | `/api/v1/venues/{venue_id}/access-rules` | Create access rule |
| PATCH | `/api/v1/access-rules/{id}` | Update access rule |
| DELETE | `/api/v1/access-rules/{id}` | Deactivate access rule |

### Reservations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/reservations` | List reservations (filterable by date, status) |
| POST | `/api/v1/venues/{venue_id}/reservations` | Create reservation |
| GET | `/api/v1/reservations/{id}` | Get reservation |
| PATCH | `/api/v1/reservations/{id}` | Update reservation (status, table, notes) |
| POST | `/api/v1/reservations/{id}/cancel` | Cancel reservation |
| GET | `/api/v1/venues/{venue_id}/availability` | Get available slots for date + party size |

### Waitlist

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/waitlist` | List active waitlist entries |
| POST | `/api/v1/venues/{venue_id}/waitlist` | Add to waitlist |
| PATCH | `/api/v1/waitlist/{id}` | Update entry (status, notes) |

### Guests

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/guests` | List/search guests in org |
| POST | `/api/v1/guests` | Create guest profile |
| GET | `/api/v1/guests/{id}` | Get guest with visit history |
| PATCH | `/api/v1/guests/{id}` | Update guest |
| GET | `/api/v1/guests/{id}/visits` | Get visit history |
| POST | `/api/v1/guests/{id}/tags` | Add tag to guest |
| DELETE | `/api/v1/guests/{id}/tags/{tag_id}` | Remove tag from guest |

### Tags

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tags` | List tags in org |
| POST | `/api/v1/tags` | Create tag |
| PATCH | `/api/v1/tags/{id}` | Update tag |
| DELETE | `/api/v1/tags/{id}` | Delete tag |

### Surveys

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/venues/{venue_id}/surveys` | List surveys (filterable) |
| POST | `/api/v1/surveys` | Submit survey (public, token-authenticated) |
| GET | `/api/v1/surveys/{id}` | Get survey |
| GET | `/api/v1/venues/{venue_id}/surveys/stats` | Aggregated survey stats |

---

## Development Phases

### Phase 1: Foundation

**Goal**: Project scaffold, data model, migrations, basic CRUD.

| Task | Details |
|------|---------|
| Project structure | Monorepo with `frontend/` and `backend/` directories |
| Docker setup | `docker-compose.yml` with PostgreSQL, FastAPI, and Next.js services |
| Database schema | All models defined in SQLAlchemy, initial Alembic migration |
| Auth | JWT-based auth with register, login, refresh |
| Org/Venue/User CRUD | Full CRUD endpoints with role-based access |
| API envelope | Consistent response format, error handling, validation |
| OpenAPI docs | Auto-generated and verified |
| Seed data | Script to populate a demo org with venues, users, floor plans, tables |

**Exit criteria**: A developer can `docker-compose up`, register an org, create venues, and manage users via the API.

### Phase 2: Reservations Core

**Goal**: Working reservation flow from availability check to completion.

| Task | Details |
|------|---------|
| Access rules CRUD | Create and manage availability rules per venue |
| Availability engine | Query endpoint that returns open slots given date + party size |
| Reservation CRUD | Create, update status, cancel |
| Reservation status machine | Enforce valid transitions |
| Waitlist CRUD | Add, update, seat from waitlist |
| Booking widget (frontend) | Embeddable Next.js component: date picker → party size → time slots → guest info → confirm |
| Staff reservation view (frontend) | Daily timeline/list view of all reservations for a venue |

**Exit criteria**: A guest can book through the widget. Staff can manage reservations, advance statuses, and manage the waitlist.

### Phase 3: Table Management

**Goal**: Visual floor plan with live seating status.

| Task | Details |
|------|---------|
| Floor plan CRUD | Create/edit floor plans per venue |
| Table CRUD | Add/edit/remove tables on a floor plan |
| Floor plan editor (frontend) | Canvas-based drag-and-drop table placement |
| Live seating view (frontend) | Floor plan rendered with color-coded table statuses |
| Table assignment | Assign reservation to table (manual) |
| Server sections | Assign servers to sections for a shift |
| Pacing view (frontend) | Covers-per-slot bar chart |
| Pre-shift report | Generate and display report for upcoming shift |

**Exit criteria**: Staff can design floor plans, assign tables to reservations, see real-time table status, and generate pre-shift reports.

### Phase 4: CRM & Surveys

**Goal**: Guest profiles with tagging, segmentation, and post-visit feedback.

| Task | Details |
|------|---------|
| Auto-profile creation | Hook into reservation/waitlist/survey creation to upsert profiles |
| Guest profile page (frontend) | Profile details, visit timeline, tags, survey responses |
| Tag CRUD | Create/manage manual and auto tags |
| Auto-tag rule engine | Define rules, run on schedule and on reservation completion |
| Guest search + segmentation (frontend) | Filterable guest list with tag, visit, and spend filters |
| Survey submission endpoint | Public endpoint for guests to submit feedback |
| Survey link generation | Generate unique token-authenticated survey URLs |
| Survey dashboard (frontend) | Rating averages, distributions, recent comments |

**Exit criteria**: Guest profiles are auto-built and enriched. Staff can tag, segment, and view guest history. Surveys are collected and displayed.

---

## Project Structure

```
openrooms/
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   ├── components/       # Shared UI components
│   │   ├── lib/              # API client, utils, types
│   │   └── styles/           # Tailwind config, globals
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/           # Route handlers grouped by module
│   │   ├── core/             # Config, security, dependencies
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (availability, rules, etc.)
│   │   └── main.py           # FastAPI app entrypoint
│   ├── alembic/              # Migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── docs/
│   └── v1-blueprint.md
└── README.md
```

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Response time (API) | < 200ms p95 for CRUD, < 500ms p95 for availability queries |
| Concurrent users | Support 50 concurrent staff users per org without degradation |
| Data retention | No auto-deletion; all data retained until org requests removal |
| Timezone handling | All times stored as UTC in database; converted to venue timezone in API responses |
| Soft deletes | All primary entities use `is_active` flag rather than hard deletes |
| Audit trail | `created_at` and `updated_at` on all entities; full audit log is a future enhancement |

---

## Open Questions

These are decisions to finalize during implementation:

1. **Booking widget delivery**: iframe embed vs. Web Component vs. hosted page with redirect?
2. **Real-time updates**: WebSockets for live floor plan status, or polling on short interval?
3. **Auto-tag rule storage**: JSON column on Tag model vs. separate `AutoTagRule` table?
4. **Survey delivery**: Generate link only (V1) vs. basic email sending via SMTP?
5. **Table turn time estimation**: Simple average of last N completed reservations, or configurable per access rule?
