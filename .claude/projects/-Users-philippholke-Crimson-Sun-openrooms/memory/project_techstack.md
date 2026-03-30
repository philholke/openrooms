---
name: Tech Stack Decisions
description: Core tech stack choices — Next.js frontend, FastAPI backend, Postgres DB (portable, Supabase-compatible)
type: project
---

**Stack:**
- Frontend: Next.js
- Backend: FastAPI (Python)
- Database: PostgreSQL

**Why:** Next.js for SSR/SSG flexibility and React ecosystem. FastAPI for async Python with auto-generated OpenAPI docs. Postgres for reliability and broad hosting options.

**How to apply:**
- DB layer must be portable — no Supabase-specific features in core schema. Use standard SQL/SQLAlchemy so it runs on any Postgres (AWS RDS, Fly.io, self-hosted, Supabase).
- If Supabase is used initially, treat it as "just Postgres" — avoid Supabase auth, storage, realtime unless explicitly opted in.
- Background jobs are out of scope for now.
