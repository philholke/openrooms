"""
Reservation service — CRUD, status machine, and side-effect triggers.
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

from app.models.guest import GuestVisit
from app.models.reservation import AccessRule, Reservation
from app.models.floor_plan import Table
from app.schemas.guest import GuestRead
from app.schemas.reservation import (
    ReservationCreate,
    ReservationRead,
    ReservationUpdate,
)
from app.services.availability import get_available_slots
from app.services.guest import get_or_create_guest

# ─── Status Machine ──────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"arrived", "partially_arrived", "cancelled", "no_show"},
    "arrived": {"seated", "cancelled", "no_show"},
    "partially_arrived": {"seated", "cancelled", "no_show"},
    "seated": {"completed"},
    "completed": set(),  # terminal
    "no_show": set(),  # terminal
    "cancelled": set(),  # terminal
}


def validate_transition(current: str, target: str) -> None:
    """Raise HTTP 409 if the transition is not allowed."""
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from '{current}' to '{target}'. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}",
        )


# ─── Helpers ─────────────────────────────────────────────────────────────

def _to_read(reservation: Reservation) -> ReservationRead:
    """Convert a Reservation ORM instance to a ReservationRead schema,
    populating nested fields from eagerly loaded relationships."""
    data = ReservationRead.model_validate(reservation)

    if reservation.guest:
        data.guest = GuestRead.model_validate(reservation.guest)
    if reservation.table:
        data.table_label = reservation.table.label
    if reservation.access_rule:
        data.access_rule_name = reservation.access_rule.name

    return data


def _base_query():
    """Return a select() with standard eager loads for reservation reads."""
    return (
        select(Reservation)
        .options(
            joinedload(Reservation.guest),
            joinedload(Reservation.table),
            joinedload(Reservation.access_rule),
        )
    )


# ─── CRUD ────────────────────────────────────────────────────────────────

async def create_reservation(
    db: AsyncSession,
    venue_id: uuid.UUID,
    org_id: uuid.UUID,
    data: ReservationCreate,
    *,
    venue_timezone: str = "UTC",
) -> ReservationRead:
    """Create a reservation, validating slot availability and upserting the guest."""

    # 1. Lock existing reservations for this venue+date to prevent concurrent
    #    overbooking.  The FOR UPDATE lock serialises concurrent inserts that
    #    target the same slot, so the availability count is always accurate.
    from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: F811

    await db.execute(
        select(Reservation.id)
        .where(
            Reservation.venue_id == venue_id,
            Reservation.date == data.date,
            Reservation.status.in_({"pending", "confirmed", "arrived", "partially_arrived", "seated"}),
        )
        .with_for_update()
    )

    # Now check availability with the lock held
    slots = await get_available_slots(
        db, venue_id, data.date, data.party_size, venue_timezone=venue_timezone
    )
    matching = [
        s for s in slots
        if s.time == data.time and s.access_rule_id == data.access_rule_id
    ]
    if not matching:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Selected time slot is no longer available",
        )

    # 2. Upsert guest profile
    guest = await get_or_create_guest(
        db,
        org_id=org_id,
        first_name=data.guest.first_name,
        last_name=data.guest.last_name,
        email=data.guest.email,
        phone=data.guest.phone,
    )

    # 3. Determine initial status
    rule_result = await db.execute(
        select(AccessRule).where(AccessRule.id == data.access_rule_id)
    )
    rule = rule_result.scalar_one_or_none()
    initial_status = "pending" if (rule and rule.require_deposit) else "confirmed"

    # 4. Create reservation
    reservation = Reservation(
        venue_id=venue_id,
        guest_id=guest.id,
        access_rule_id=data.access_rule_id,
        date=data.date,
        time=data.time,
        party_size=data.party_size,
        status=initial_status,
        source=data.source,
        special_requests=data.special_requests,
        cancel_token=secrets.token_urlsafe(32),
    )
    db.add(reservation)
    await db.flush()

    logger.info(
        "Reservation created: id=%s venue=%s date=%s time=%s party=%d source=%s",
        reservation.id, venue_id, data.date, data.time, data.party_size, data.source,
    )

    # Reload with relationships
    result = await db.execute(
        _base_query().where(Reservation.id == reservation.id)
    )
    reservation = result.unique().scalar_one()
    return _to_read(reservation)


async def list_reservations(
    db: AsyncSession,
    venue_id: uuid.UUID,
    *,
    date: "date | None" = None,
    statuses: list[str] | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[ReservationRead], int]:
    """List reservations with filters. Returns (items, total_count)."""
    from datetime import date as date_type
    from app.models.guest import GuestProfile

    base = select(Reservation).where(Reservation.venue_id == venue_id)

    if date is not None:
        base = base.where(Reservation.date == date)
    if statuses:
        base = base.where(Reservation.status.in_(statuses))
    if search:
        pattern = f"%{search}%"
        base = base.join(Reservation.guest).where(
            GuestProfile.first_name.ilike(pattern)
            | GuestProfile.last_name.ilike(pattern)
        )

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    # Paginated + eager loaded query
    stmt = (
        _base_query()
        .where(Reservation.venue_id == venue_id)
    )
    if date is not None:
        stmt = stmt.where(Reservation.date == date)
    if statuses:
        stmt = stmt.where(Reservation.status.in_(statuses))
    if search:
        pattern = f"%{search}%"
        # Already joining guest via joinedload, add filter
        from app.models.guest import GuestProfile
        stmt = stmt.where(
            Reservation.guest.has(
                GuestProfile.first_name.ilike(pattern)
                | GuestProfile.last_name.ilike(pattern)
            )
        )

    stmt = stmt.order_by(Reservation.time, Reservation.id).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    reservations = result.unique().scalars().all()

    return [_to_read(r) for r in reservations], total


async def get_reservation(
    db: AsyncSession,
    reservation_id: uuid.UUID,
    venue_id: uuid.UUID,
) -> ReservationRead:
    result = await db.execute(
        _base_query().where(
            Reservation.id == reservation_id,
            Reservation.venue_id == venue_id,
        )
    )
    reservation = result.unique().scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    return _to_read(reservation)


async def update_reservation(
    db: AsyncSession,
    reservation_id: uuid.UUID,
    venue_id: uuid.UUID,
    data: ReservationUpdate,
) -> ReservationRead:
    result = await db.execute(
        _base_query().where(
            Reservation.id == reservation_id,
            Reservation.venue_id == venue_id,
        )
    )
    reservation = result.unique().scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reservation, field, value)

    await db.flush()
    await db.refresh(reservation)

    # Reload with relationships
    result = await db.execute(
        _base_query().where(Reservation.id == reservation.id)
    )
    reservation = result.unique().scalar_one()
    return _to_read(reservation)


async def update_status(
    db: AsyncSession,
    reservation_id: uuid.UUID,
    venue_id: uuid.UUID,
    new_status: str,
) -> ReservationRead:
    """Advance the reservation status with side effects."""
    # Lock the row to prevent concurrent status transitions
    await db.execute(
        select(Reservation.id)
        .where(Reservation.id == reservation_id)
        .with_for_update()
    )

    result = await db.execute(
        _base_query().where(
            Reservation.id == reservation_id,
            Reservation.venue_id == venue_id,
        )
    )
    reservation = result.unique().scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")

    validate_transition(reservation.status, new_status)
    logger.info(
        "Reservation %s status: %s -> %s", reservation_id, reservation.status, new_status,
    )
    reservation.status = new_status

    # ── Side effects ──
    if new_status == "completed":
        visit = GuestVisit(
            guest_id=reservation.guest_id,
            venue_id=reservation.venue_id,
            reservation_id=reservation.id,
            visited_at=datetime.now(timezone.utc),
        )
        db.add(visit)

    if new_status == "cancelled":
        reservation.cancelled_at = datetime.now(timezone.utc)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        _base_query().where(Reservation.id == reservation.id)
    )
    reservation = result.unique().scalar_one()
    return _to_read(reservation)


async def cancel_reservation(
    db: AsyncSession,
    reservation_id: uuid.UUID,
    venue_id: uuid.UUID,
    reason: str | None = None,
) -> ReservationRead:
    """Cancel a reservation — convenience wrapper around update_status."""
    result = await db.execute(
        _base_query().where(
            Reservation.id == reservation_id,
            Reservation.venue_id == venue_id,
        )
    )
    reservation = result.unique().scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")

    validate_transition(reservation.status, "cancelled")
    logger.info("Reservation %s cancelled (reason: %s)", reservation_id, reason or "none")
    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now(timezone.utc)
    if reason:
        existing_notes = reservation.notes or ""
        reservation.notes = f"{existing_notes}\n[Cancelled] {reason}".strip()

    await db.flush()

    result = await db.execute(
        _base_query().where(Reservation.id == reservation.id)
    )
    reservation = result.unique().scalar_one()
    return _to_read(reservation)
