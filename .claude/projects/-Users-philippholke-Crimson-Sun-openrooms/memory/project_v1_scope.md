---
name: V1 Scope
description: V1 is modules 1-3 + post-visit surveys only. No marketing, ordering, loyalty, AI, events, or external integrations.
type: project
---

**V1 modules (only):**
1. Reservations & Waitlist — booking widget, access rules, deposits, waitlist, cancellation policies
2. Table Management — floor plan, seating, server assignment, pacing, pre-shift reports
3. CRM & Guest Profiles — auto-built profiles, tags, auto-tags, segmentation
4. Post-Visit Surveys (from Module 7) — feedback collection and display, no review aggregation from external platforms

**Explicitly out of scope for V1:**
- Marketing Automation (email/SMS campaigns)
- Events, Experiences & Add-Ons
- Online Ordering
- Loyalty, VIP & Retention (priority alerts, private line, referrals)
- AI Features
- External integrations (POS, Twilio, Stripe, Google/Facebook booking channels)
- Reputation management beyond our own surveys (no Google/Yelp/TripAdvisor aggregation)
- Reporting & Analytics (beyond basic operational views)

**Why:** These 3.5 modules form the core reservation operations loop. Everything else layers on top. Ship a solid foundation first.

**How to apply:** Design the data model to accommodate future modules (don't close doors), but don't build any scaffolding or placeholder code for out-of-scope features.
