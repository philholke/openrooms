<p align="center">
  <img src="docs/logo.svg" width="120" alt="OpenRooms logo" />
</p>

<h1 align="center">OpenRooms</h1>

<p align="center">
  Open-source restaurant reservation &amp; guest management platform.<br/>
  A self-hostable alternative to SevenRooms — no per-cover fees, no vendor lock-in.
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a>&ensp;&middot;&ensp;
  <a href="docs/v1-blueprint.md">Blueprint</a>&ensp;&middot;&ensp;
  <a href="docs/changelog.md">Changelog</a>&ensp;&middot;&ensp;
  <a href="#license">License</a>
</p>

---

## What is OpenRooms?

OpenRooms gives restaurants the same tools that enterprise platforms charge $500+/month for:

- **Reservation system** with access rules, availability engine, and pacing controls
- **Guest-facing booking widget** — embeddable 5-step flow, mobile-first
- **Staff dashboard** — manage reservations, waitlist, and table assignments
- **CRM & guest profiles** — auto-created on every booking, org-scoped, deduplicated
- **Waitlist management** — walk-in tracking with automatic reservation bridging
- **Multi-tenant** — one install serves multiple organizations, each with multiple venues

Your data stays on your infrastructure. Deploy anywhere: Docker, Fly.io, Railway, AWS, or bare metal.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Docker Compose                     │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Frontend    │  │   Backend    │  │ PostgreSQL │ │
│  │   Next.js 15  │  │   FastAPI    │  │     16     │ │
│  │   React 19    │──│   async      │──│            │ │
│  │   Tailwind 4  │  │  SQLAlchemy  │  │  UUID PKs  │ │
│  │     :3000     │  │    :8000     │  │   :5432    │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└──────────────────────────────────────────────────────┘
```

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| **Database** | PostgreSQL 16 — works with Supabase, RDS, Neon, or self-hosted |
| **Auth** | JWT (access + refresh tokens), role-based (owner/admin/manager/staff) |
| **API** | RESTful at `/api/v1/`, consistent JSON envelope, OpenAPI docs at `/docs` |

### Multi-Tenancy

**Organization** is the tenant boundary. An org has many **Venues**; guest profiles are shared across venues within an org. A single restaurant is simply an org with one venue — no special case.

```
Organization
├── Users (owner, admin, manager, staff)
├── GuestProfiles (org-scoped, deduped by email)
│   ├── Tags (many-to-many)
│   ├── GuestVisits (per-venue history)
│   └── Surveys
└── Venues
    ├── FloorPlans → Tables
    ├── AccessRules (availability, pacing, policies)
    ├── Reservations (pending → confirmed → arrived → seated → completed)
    └── WaitlistEntries
```

## Quickstart

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Run

```bash
git clone https://github.com/your-org/openrooms.git
cd openrooms
docker-compose up
```

| Service | URL |
|---------|-----|
| Frontend | [http://localhost:3000](http://localhost:3000) |
| Backend API | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Database | `localhost:5432` |

### Seed Data

After the stack is up, load demo data (organization, venues, users, floor plans, tables, access rules, guests):

```bash
docker-compose exec backend python -m scripts.seed
```

### Default Credentials (Seed)

| Role | Email | Password |
|------|-------|----------|
| Owner | `owner@demo.com` | `password123` |
| Manager | `manager@demo.com` | `password123` |
| Staff | `staff@demo.com` | `password123` |

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Migrations (requires a running PostgreSQL):

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Both services read from `.env` files (gitignored). See `docker-compose.yml` for the full list. Key variables:

| Variable | Service | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | Backend | Async connection (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Backend | Alembic migrations (`postgresql+psycopg2://...`) |
| `SECRET_KEY` | Backend | JWT signing key |
| `CORS_ORIGINS` | Backend | Allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend URL for API calls |

## V1 Modules

| Module | Status | Description |
|--------|--------|-------------|
| Reservations & Waitlist | **Complete** | Access rules, availability engine, booking widget, waitlist with walk-in bridging |
| Table Management | **Partial** | Floor plans, tables, and table assignment (interactive floor plan UI is future) |
| CRM & Guest Profiles | **Complete** | Auto-creation, deduplication, visit tracking, tagging |
| Post-Visit Surveys | **Schema only** | Model exists, endpoints planned |

See the [V1 Blueprint](docs/v1-blueprint.md) for the full specification and [Changelog](docs/changelog.md) for release history.

## Project Structure

```
openrooms/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers
│   │   ├── core/            # Config, database, security
│   │   ├── models/          # SQLAlchemy 2.0 models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic layer
│   ├── alembic/             # Database migrations
│   ├── scripts/             # Seed data, utilities
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages
│       ├── components/      # UI primitives (Button, Modal, Card, etc.)
│       ├── contexts/        # Auth & Venue context providers
│       ├── lib/             # API client, types, utilities
│       └── ...
├── docker-compose.yml
└── docs/
    ├── v1-blueprint.md      # Full technical specification
    ├── vision.md            # SevenRooms feature reference
    └── changelog.md         # Release history
```

## Contributing

Contributions are welcome. Please:

1. Fork the repo and create a feature branch
2. Follow existing code conventions (the codebase is the style guide)
3. Test your changes with `docker-compose up` before submitting
4. Open a PR against `main` with a clear description of what and why

## License

Dual-licensed under [MIT](LICENSE-MIT) and [Apache 2.0](LICENSE-APACHE) — use whichever fits your needs.

---

<p align="center">
  Built by <a href="https://github.com/philholke">Philipp Holke</a> &middot; <a href="https://github.com/your-org/openrooms">GitHub</a>
</p>
