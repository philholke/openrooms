"""
Guest profile service — upsert from bookings + full CRUD for the CRM.

Every reservation or waitlist entry flows through get_or_create_guest() to
ensure we never create duplicate profiles for the same person within an org.

Phase 4A adds list/detail/create/update for the staff-facing CRM.
"""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.guest import GuestProfile, GuestVisit, guest_tags
from app.models.survey import Survey
from app.models.tag import Tag
from app.models.venue import Venue
from app.schemas.guest import (
    GuestCreate,
    GuestDetailRead,
    GuestListRead,
    GuestRead,
    GuestUpdate,
    GuestVisitRead,
)
from app.schemas.survey import SurveyRead
from app.schemas.tag import TagRead

logger = logging.getLogger(__name__)


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
        # Use a SAVEPOINT so that only this insert rolls back on conflict,
        # preserving the outer transaction (and any FOR UPDATE locks).
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        # Concurrent insert with same (org_id, email) — the SAVEPOINT was
        # rolled back; the outer transaction is still intact.
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


# ─── CRUD (Phase 4A) ─────────────────────────────────────────────────────


def _escape_like(value: str) -> str:
    """Escape LIKE special characters in a search term."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_guests(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    search: str | None = None,
    tag_id: uuid.UUID | None = None,
    venue_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[GuestListRead], int]:
    """
    List guests in an org with optional search, tag filter, and venue filter.

    Returns lightweight GuestListRead objects with visit count and tag names.
    """
    base = select(GuestProfile).where(GuestProfile.org_id == org_id)

    if search:
        pattern = f"%{_escape_like(search)}%"
        base = base.where(
            or_(
                GuestProfile.first_name.ilike(pattern),
                GuestProfile.last_name.ilike(pattern),
                GuestProfile.email.ilike(pattern),
            )
        )

    if tag_id:
        base = base.where(
            GuestProfile.id.in_(
                select(guest_tags.c.guest_id).where(guest_tags.c.tag_id == tag_id)
            )
        )

    if venue_id:
        base = base.where(
            GuestProfile.id.in_(
                select(GuestVisit.guest_id).where(GuestVisit.venue_id == venue_id)
            )
        )

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    # Fetch guests with tags eager-loaded
    stmt = (
        base.options(selectinload(GuestProfile.tags))
        .order_by(GuestProfile.last_name, GuestProfile.first_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    guests = result.scalars().unique().all()

    # Compute visit counts in a single query for this page of guests
    guest_ids = [g.id for g in guests]
    visit_counts: dict[uuid.UUID, int] = {}
    if guest_ids:
        vc_result = await db.execute(
            select(GuestVisit.guest_id, func.count())
            .where(GuestVisit.guest_id.in_(guest_ids))
            .group_by(GuestVisit.guest_id)
        )
        visit_counts = dict(vc_result.all())

    items = [
        GuestListRead(
            id=g.id,
            org_id=g.org_id,
            first_name=g.first_name,
            last_name=g.last_name,
            email=g.email,
            phone=g.phone,
            total_visits=visit_counts.get(g.id, 0),
            tag_names=[t.name for t in g.tags],
            created_at=g.created_at,
        )
        for g in guests
    ]
    return items, total


async def get_guest_detail(
    db: AsyncSession,
    guest_id: uuid.UUID,
    org_id: uuid.UUID,
) -> GuestDetailRead:
    """
    Full guest profile with tags, recent visits, recent surveys, and stats.

    Visits limited to last 10, surveys to last 5 — keeps payloads manageable
    while giving staff enough context.
    """
    result = await db.execute(
        select(GuestProfile)
        .options(selectinload(GuestProfile.tags))
        .where(GuestProfile.id == guest_id, GuestProfile.org_id == org_id)
    )
    guest = result.scalar_one_or_none()
    if guest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found")

    # Recent visits with venue name (last 10)
    # Join through Venue and filter by org_id for defense-in-depth
    visits_result = await db.execute(
        select(GuestVisit, Venue.name.label("venue_name"))
        .join(Venue, GuestVisit.venue_id == Venue.id)
        .where(GuestVisit.guest_id == guest_id, Venue.org_id == org_id)
        .order_by(GuestVisit.visited_at.desc())
        .limit(10)
    )
    visit_rows = visits_result.all()
    visits = [
        GuestVisitRead(
            id=row.GuestVisit.id,
            venue_id=row.GuestVisit.venue_id,
            venue_name=row.venue_name,
            reservation_id=row.GuestVisit.reservation_id,
            visited_at=row.GuestVisit.visited_at,
            spend_amount=row.GuestVisit.spend_amount,
            notes=row.GuestVisit.notes,
        )
        for row in visit_rows
    ]

    # Recent surveys (last 5) — org-scoped via venue join
    surveys_result = await db.execute(
        select(Survey)
        .join(Venue, Survey.venue_id == Venue.id)
        .where(Survey.guest_id == guest_id, Venue.org_id == org_id)
        .order_by(Survey.created_at.desc())
        .limit(5)
    )
    surveys = [SurveyRead.model_validate(s) for s in surveys_result.scalars().all()]

    # Aggregate stats — org-scoped via venue join
    stats_result = await db.execute(
        select(
            func.count().label("total_visits"),
            func.max(GuestVisit.visited_at).label("last_visit_date"),
        )
        .join(Venue, GuestVisit.venue_id == Venue.id)
        .where(GuestVisit.guest_id == guest_id, Venue.org_id == org_id)
    )
    stats = stats_result.one()

    avg_rating_result = await db.execute(
        select(func.avg(Survey.overall_rating))
        .join(Venue, Survey.venue_id == Venue.id)
        .where(Survey.guest_id == guest_id, Venue.org_id == org_id)
    )
    avg_rating = avg_rating_result.scalar_one_or_none()

    return GuestDetailRead(
        id=guest.id,
        org_id=guest.org_id,
        first_name=guest.first_name,
        last_name=guest.last_name,
        email=guest.email,
        phone=guest.phone,
        birthday=guest.birthday,
        anniversary=guest.anniversary,
        dietary_restrictions=guest.dietary_restrictions,
        notes=guest.notes,
        created_at=guest.created_at,
        updated_at=guest.updated_at,
        tags=[TagRead.model_validate(t) for t in guest.tags],
        visits=visits,
        surveys=surveys,
        total_visits=stats.total_visits,
        last_visit_date=stats.last_visit_date,
        avg_overall_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
    )


async def create_guest(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: GuestCreate,
) -> GuestRead:
    """
    Manually create a guest profile. Checks for email dedup within the org.
    """
    if data.email:
        existing = await db.execute(
            select(GuestProfile.id).where(
                GuestProfile.org_id == org_id,
                GuestProfile.email == data.email,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A guest with this email already exists in the organization",
            )

    guest = GuestProfile(org_id=org_id, **data.model_dump())
    db.add(guest)
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A guest with this email already exists in the organization",
        )
    await db.refresh(guest)

    logger.info("Guest created: id=%s org=%s email=%s", guest.id, org_id, data.email)
    return GuestRead.model_validate(guest)


async def update_guest(
    db: AsyncSession,
    guest_id: uuid.UUID,
    org_id: uuid.UUID,
    data: GuestUpdate,
) -> GuestRead:
    """Partial update of a guest profile using exclude_unset."""
    result = await db.execute(
        select(GuestProfile).where(
            GuestProfile.id == guest_id,
            GuestProfile.org_id == org_id,
        )
    )
    guest = result.scalar_one_or_none()
    if guest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return GuestRead.model_validate(guest)

    # If email is being changed, check for duplicates
    new_email = update_data.get("email")
    if new_email is not None and new_email != guest.email:
        dup_result = await db.execute(
            select(GuestProfile.id).where(
                GuestProfile.org_id == org_id,
                GuestProfile.email == new_email,
                GuestProfile.id != guest_id,
            )
        )
        if dup_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A guest with this email already exists in the organization",
            )

    for field, value in update_data.items():
        setattr(guest, field, value)

    await db.flush()
    await db.refresh(guest)

    logger.info("Guest updated: id=%s org=%s", guest_id, org_id)
    return GuestRead.model_validate(guest)
