# Changelog

---

## Index

### 0.1.0 — Project Scaffold (2026-03-30)

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
