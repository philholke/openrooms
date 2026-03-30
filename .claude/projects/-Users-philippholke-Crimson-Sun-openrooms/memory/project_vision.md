---
name: OpenRooms Project Vision
description: Open-source SevenRooms clone — hospitality platform with reservations, table management, CRM, marketing automation, events, ordering, reputation mgmt
type: project
---

OpenRooms aims to be an open-source SevenRooms clone that works >80% as well, cutting unimportant commercial fluff.

**Why:** SevenRooms charges $499-700+/month per venue with annual contracts. An open-source alternative would democratize access to hospitality tech.

**How to apply:** Focus on the core modules that ground ops actually need. The 11 modules in priority are:
1. Reservations & Waitlist (core booking engine + widget)
2. Table Management (floor plan, seating, host stand ops)
3. CRM & Guest Profiles (central data layer, auto-tags)
4. Marketing Automation (trigger-based campaigns)
5. Events, Experiences & Add-Ons
6. Online Ordering (commission-free)
7. Reputation Management (review aggregation)
8. Reporting & Analytics
9. Loyalty, VIP & Retention
10. AI Features
11. Integrations (POS, payment, SMS, booking channels)

Key architecture: Venue is multi-tenant root, Guest Profile is central entity (100+ data points), everything writes to CRM. Background jobs for auto-tags, campaign triggers, waitlist pacing, priority alerts.
