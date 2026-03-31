"""
Seed script — populates the database with demo data for development.

Usage (from backend/):
    python -m scripts.seed

Requires: a running Postgres with migrations applied (alembic upgrade head).
"""

import asyncio
import sys
from datetime import date, time
from pathlib import Path

# Ensure the backend package is importable when running as `python -m scripts.seed`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.floor_plan import FloorPlan, Table
from app.models.guest import GuestProfile
from app.models.organization import Organization
from app.models.reservation import AccessRule
from app.models.user import User
from app.models.venue import Venue


async def seed() -> None:
    async with async_session_factory() as db:
        # Idempotency: skip if the demo org already exists
        existing = await db.execute(
            select(Organization).where(Organization.slug == "demo")
        )
        if existing.scalar_one_or_none():
            print("Seed data already exists — skipping.")
            return

        # ── Organization ──────────────────────────────────────────────
        org = Organization(name="Demo Restaurant Group", slug="demo")
        db.add(org)
        await db.flush()

        # ── Users ─────────────────────────────────────────────────────
        users = [
            User(
                org_id=org.id,
                email="owner@demo.com",
                hashed_password=hash_password("password"),
                full_name="Alex Owner",
                role="owner",
            ),
            User(
                org_id=org.id,
                email="manager@demo.com",
                hashed_password=hash_password("password"),
                full_name="Jordan Manager",
                role="manager",
            ),
            User(
                org_id=org.id,
                email="staff@demo.com",
                hashed_password=hash_password("password"),
                full_name="Sam Staff",
                role="staff",
            ),
        ]
        db.add_all(users)
        await db.flush()

        # ── Venues ────────────────────────────────────────────────────
        downtown = Venue(
            org_id=org.id,
            name="Downtown Bistro",
            slug="downtown-bistro",
            address="42 Main Street, Anytown, USA",
            timezone="America/New_York",
            phone="+1-555-0101",
            email="downtown@demo.com",
        )
        waterfront = Venue(
            org_id=org.id,
            name="Waterfront Grill",
            slug="waterfront-grill",
            address="7 Harbor Drive, Anytown, USA",
            timezone="America/New_York",
            phone="+1-555-0102",
            email="waterfront@demo.com",
        )
        db.add_all([downtown, waterfront])
        await db.flush()

        # ── Floor Plans & Tables ──────────────────────────────────────
        for venue, plan_name, tables_spec in [
            (
                downtown,
                "Main Floor",
                [
                    ("T1", 2, 2, "Window"),
                    ("T2", 2, 2, "Window"),
                    ("T3", 2, 4, "Main"),
                    ("T4", 2, 4, "Main"),
                    ("T5", 4, 6, "Main"),
                    ("T6", 4, 6, "Main"),
                    ("T7", 6, 8, "Private"),
                    ("T8", 8, 12, "Private"),
                    ("B1", 1, 2, "Bar"),
                    ("B2", 1, 2, "Bar"),
                ],
            ),
            (
                waterfront,
                "Deck & Interior",
                [
                    ("D1", 2, 4, "Deck"),
                    ("D2", 2, 4, "Deck"),
                    ("D3", 4, 6, "Deck"),
                    ("D4", 4, 6, "Deck"),
                    ("I1", 2, 2, "Interior"),
                    ("I2", 2, 4, "Interior"),
                    ("I3", 4, 6, "Interior"),
                    ("I4", 6, 8, "Interior"),
                    ("I5", 8, 10, "Interior"),
                    ("P1", 10, 20, "Private Dining"),
                    ("B1", 1, 2, "Bar"),
                    ("B2", 1, 2, "Bar"),
                ],
            ),
        ]:
            fp = FloorPlan(venue_id=venue.id, name=plan_name)
            db.add(fp)
            await db.flush()

            x = 0.0
            for label, min_cap, max_cap, section in tables_spec:
                db.add(
                    Table(
                        floor_plan_id=fp.id,
                        label=label,
                        min_capacity=min_cap,
                        max_capacity=max_cap,
                        section=section,
                        x_position=x,
                        y_position=0.0,
                        shape="circle" if label.startswith("B") else "rectangle",
                    )
                )
                x += 1.0

        await db.flush()

        # ── Access Rules ──────────────────────────────────────────────
        for venue in [downtown, waterfront]:
            rules = [
                AccessRule(
                    venue_id=venue.id,
                    name="Lunch",
                    days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
                    start_time=time(11, 30),
                    end_time=time(14, 0),
                    slot_interval_minutes=30,
                    min_party_size=1,
                    max_party_size=8,
                    max_covers_per_slot=20,
                    advance_booking_days=14,
                    cutoff_minutes=60,
                ),
                AccessRule(
                    venue_id=venue.id,
                    name="Dinner",
                    days_of_week=[0, 1, 2, 3, 4, 5, 6],  # Every day
                    start_time=time(17, 30),
                    end_time=time(21, 30),
                    slot_interval_minutes=30,
                    min_party_size=1,
                    max_party_size=12,
                    max_covers_per_slot=30,
                    advance_booking_days=30,
                    cutoff_minutes=120,
                ),
                AccessRule(
                    venue_id=venue.id,
                    name="Weekend Brunch",
                    days_of_week=[5, 6],  # Sat-Sun
                    start_time=time(10, 0),
                    end_time=time(14, 0),
                    slot_interval_minutes=30,
                    min_party_size=1,
                    max_party_size=10,
                    max_covers_per_slot=25,
                    advance_booking_days=14,
                    cutoff_minutes=60,
                ),
            ]
            db.add_all(rules)

        await db.flush()

        # ── Guest Profiles ────────────────────────────────────────────
        guests = [
            GuestProfile(
                org_id=org.id,
                first_name="Emily",
                last_name="Chen",
                email="emily.chen@example.com",
                phone="+1-555-1001",
                dietary_restrictions="Vegetarian",
            ),
            GuestProfile(
                org_id=org.id,
                first_name="Marcus",
                last_name="Johnson",
                email="marcus.j@example.com",
                phone="+1-555-1002",
                birthday=date(1985, 7, 15),
            ),
            GuestProfile(
                org_id=org.id,
                first_name="Sofia",
                last_name="Rodriguez",
                email="sofia.r@example.com",
                phone="+1-555-1003",
                notes="Prefers window seating. Regular customer.",
            ),
            GuestProfile(
                org_id=org.id,
                first_name="James",
                last_name="Williams",
                email="james.w@example.com",
                phone="+1-555-1004",
                dietary_restrictions="Gluten-free",
                anniversary=date(2020, 6, 20),
            ),
            GuestProfile(
                org_id=org.id,
                first_name="Aisha",
                last_name="Patel",
                email="aisha.p@example.com",
                phone="+1-555-1005",
            ),
            GuestProfile(
                org_id=org.id,
                first_name="Liam",
                last_name="O'Brien",
                email="liam.ob@example.com",
                phone="+1-555-1006",
                dietary_restrictions="Nut allergy",
                notes="VIP — corporate account",
            ),
            GuestProfile(
                org_id=org.id,
                first_name="Yuki",
                last_name="Tanaka",
                email="yuki.t@example.com",
                phone="+1-555-1007",
            ),
            GuestProfile(
                org_id=org.id,
                first_name="David",
                last_name="Kim",
                email="david.kim@example.com",
                phone="+1-555-1008",
                birthday=date(1990, 12, 3),
                notes="Wine enthusiast — likes bold reds",
            ),
        ]
        db.add_all(guests)

        await db.commit()
        print("Seed data created successfully.")
        print(f"  Organization: {org.name} (slug: {org.slug})")
        print(f"  Users: owner@demo.com / manager@demo.com / staff@demo.com (password: password)")
        print(f"  Venues: {downtown.name}, {waterfront.name}")
        print(f"  Guests: {len(guests)} profiles")


if __name__ == "__main__":
    asyncio.run(seed())
