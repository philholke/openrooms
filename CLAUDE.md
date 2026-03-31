# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenRooms is an open-source SevenRooms clone for restaurant reservation management. It's a monorepo with a FastAPI backend, Next.js frontend, and PostgreSQL database, orchestrated via Docker Compose.

## Commands

### Full Stack (Docker)
```bash
docker-compose up          # Start all services (db:5432, backend:8000, frontend:3000)
docker-compose down        # Stop all services
```

### Backend (Python/FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Dev server

# Alembic migrations (run from backend/)
alembic revision --autogenerate -m "description"   # Generate migration
alembic upgrade head                                # Apply migrations
alembic downgrade -1                                # Rollback one migration
```
Alembic uses the **sync** DATABASE_URL_SYNC (psycopg2) for migrations, while the app uses the **async** DATABASE_URL (asyncpg). Both are configured in `app/core/config.py` and overridden in `alembic/env.py`.

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev       # Dev server on :3000
npm run build     # Production build (standalone output mode)
npm run start     # Run production build
npm run lint      # ESLint
```

## Architecture

### Multi-Tenancy Model
- **Organization** is the tenant boundary — all data is org-scoped.
- An org has many **Venues**; guest profiles are shared across venues within an org.
- A single restaurant is just an org with one venue (no special case).

### Backend Structure (`backend/app/`)
- `main.py` — FastAPI app entrypoint, CORS middleware, health check at `/health`
- `core/config.py` — Pydantic Settings (loads from `.env`)
- `core/database.py` — Async SQLAlchemy engine, session factory, `Base` declarative base
- `api/v1/router.py` — Versioned API router mounted at `/api/v1`
- `models/` — SQLAlchemy 2.0 models using `Mapped[]` type annotations, UUID PKs via `gen_random_uuid()`
- `models/base.py` — `TimestampMixin` with `created_at`/`updated_at` server defaults
- `schemas/` — Pydantic request/response schemas (to be built)
- `services/` — Business logic layer (to be built)

### Frontend Structure (`frontend/src/`)
- Next.js 15 App Router with React 19 and TypeScript strict mode
- Tailwind CSS 4 for styling
- Path alias: `@/*` maps to `src/*`

### Database Conventions
- All PKs are UUIDs with Postgres `gen_random_uuid()` server-side defaults
- Soft deletes via `is_active` flag (no hard deletes on primary entities)
- All times stored as UTC; converted to venue timezone in API responses
- `TimestampMixin` on all models for `created_at`/`updated_at`

### API Conventions
- RESTful at `/api/v1/`
- Consistent envelope: `{ "data": ..., "meta": { "page", "per_page", "total" }, "errors": null }`
- Auth via JWT (access + refresh tokens)
- OpenAPI docs auto-generated at `/docs`

### Key Models (Entity Hierarchy)
```
Organization
├── Users (roles: owner, admin, manager, staff)
├── GuestProfiles (org-scoped, deduped by org_id+email)
│   ├── Tags (many-to-many via guest_tags)
│   ├── GuestVisits (per-venue history)
│   └── Surveys
├── Tags (manual + auto-tags with rule engine)
└── Venues
    ├── FloorPlans → Tables
    ├── AccessRules (availability/pacing/policies)
    ├── Reservations (status machine: pending→confirmed→arrived→seated→completed)
    └── WaitlistEntries
```

### Two Database URLs
The project requires two connection strings because Alembic runs synchronous migrations while the FastAPI app uses async SQLAlchemy:
- `DATABASE_URL` — `postgresql+asyncpg://...` (app runtime)
- `DATABASE_URL_SYNC` — `postgresql+psycopg2://...` (Alembic migrations)

## V1 Scope

Four modules: (1) Reservations & Waitlist, (2) Table Management, (3) CRM & Guest Profiles, (4) Post-Visit Surveys. See `docs/v1-blueprint.md` for full specification including data model details, API endpoints, and development phases.
