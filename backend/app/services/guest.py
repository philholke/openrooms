"""
Guest profile upsert — the bridge between bookings and the CRM.

Every reservation or waitlist entry flows through get_or_create_guest() to
ensure we never create duplicate profiles for the same person within an org.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import GuestProfile


async def get_or_create_guest(
    db: AsyncSession,
    org_id: uuid.UUID,
    first_name: str,
    last_name: str,
    email: str | None = None,
    phone: str | None = None,
) -> GuestProfile:
    """
    Find an existing guest by (org_id, email) or create a new one.

    If found, enriches the profile: updates first_name/last_name/phone only
    when the existing value is NULL and the new value is non-null.
    This prevents overwriting corrections made by staff.

    If no email is provided, always creates a new profile (phone-based
    dedup is future scope).
    """
    if email:
        result = await db.execute(
            select(GuestProfile).where(
                GuestProfile.org_id == org_id,
                GuestProfile.email == email,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Enrich — fill in blanks, never overwrite existing data
            if existing.first_name is None or existing.first_name == "":
                existing.first_name = first_name
            if existing.last_name is None or existing.last_name == "":
                existing.last_name = last_name
            if existing.phone is None and phone:
                existing.phone = phone
            await db.flush()
            return existing

    # No email or no match — create new profile
    guest = GuestProfile(
        org_id=org_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )
    db.add(guest)
    try:
        await db.flush()
    except IntegrityError:
        # Concurrent insert with same (org_id, email) — roll back the
        # failed insert and fetch the winner.
        await db.rollback()
        result = await db.execute(
            select(GuestProfile).where(
                GuestProfile.org_id == org_id,
                GuestProfile.email == email,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        raise  # re-raise if it wasn't the unique constraint
    return guest
