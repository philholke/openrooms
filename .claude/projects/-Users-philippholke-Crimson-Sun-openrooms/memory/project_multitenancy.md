---
name: Multi-tenancy Model
description: Multi-tenancy is by Organization (not venue/outlet). Orgs can have 1-to-many venues. Single restaurants get a 1-venue org.
type: project
---

Multi-tenancy root is **Organization**, not Venue.

**Why:** Most users will be larger hospitality groups with multiple venues/brands. Single restaurants are just an org with one venue. Tenancy at the org level means shared guest profiles, cross-venue reporting, group-level segmentation, and unified user permissions — all core SevenRooms features (especially at Premium tier).

**How to apply:**
- `Organization` is the tenant boundary — all data isolation, billing, and access control scopes to org.
- `Venue` belongs to an org. An org can have many venues.
- Guest profiles are org-scoped (shared across venues within an org, not global).
- User permissions are per-org with optional per-venue granularity.
- Single-restaurant operators just have an org with one venue — no special case needed.
