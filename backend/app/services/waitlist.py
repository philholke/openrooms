"""
Waitlist service — manages walk-in guest flow from check-in to seating.
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

from app.models.reservation import Reservation, WaitlistEntry
from app.schemas.guest import GuestRead
from app.schemas.waitlist import WaitlistEntryCreate, WaitlistEntryRead, WaitlistEntryUpdate
from app.services.guest import get_or_create_guest

# ─── Status transitions ──────────────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "waiting": {"notified", "seated", "cancelled", "no_show"},
    "notified": {"seated", "cancelled", "no_show"},
    "seated": set(),  # terminal
    "cancelled": set(),  # terminal
    "no_show": set(),  # terminal
}


def _validate_transition(current: str, target: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition waitlist entry from '{current}' to '{target}'. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}",
        )


# ─── Helpers ─────────────────────────────────────────────────────────────

def _base_query():
    return select(WaitlistEntry).options(joinedload(WaitlistEntry.guest))


def _to_read(entry: WaitlistEntry) -> WaitlistEntryRead:
    data = WaitlistEntryRead.model_validate(entry)
    if entry.guest:
        data.guest = GuestRead.model_validate(entry.guest)
    return data


# ─── Service functions ───────────────────────────────────────────────────

async def add_to_waitlist(
    db: AsyncSession,
    venue_id: uuid.UUID,
    org_id: uuid.UUID,
    data: WaitlistEntryCreate,
) -> WaitlistEntryRead:
    """Add a walk-in guest to the waitlist."""
    guest = await get_or_create_guest(
        db,
        org_id=org_id,
        first_name=data.guest.first_name,
        last_name=data.guest.last_name,
        email=data.guest.email,
        phone=data.guest.phone,
    )

    entry = WaitlistEntry(
        venue_id=venue_id,
        guest_id=guest.id,
        party_size=data.party_size,
        quoted_wait_minutes=data.quoted_wait_minutes,
        notes=data.notes,
        check_in_time=datetime.now(timezone.utc),
        status="waiting",
    )
    db.add(entry)
    await db.flush()

    logger.info("Waitlist entry added: id=%s venue=%s party=%d", entry.id, venue_id, data.party_size)

    result = await db.execute(
        _base_query().where(WaitlistEntry.id == entry.id)
    )
    entry = result.unique().scalar_one()
    return _to_read(entry)


async def list_waitlist(
    db: AsyncSession,
    venue_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[WaitlistEntryRead]:
    """List waitlist entries for a venue, ordered FIFO by check-in time."""
    stmt = _base_query().where(WaitlistEntry.venue_id == venue_id)

    if active_only:
        stmt = stmt.where(WaitlistEntry.status.in_({"waiting", "notified"}))

    stmt = stmt.order_by(WaitlistEntry.check_in_time.asc())
    result = await db.execute(stmt)
    entries = result.unique().scalars().all()
    return [_to_read(e) for e in entries]


async def update_waitlist_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    venue_id: uuid.UUID,
    data: WaitlistEntryUpdate,
) -> WaitlistEntryRead:
    """Update a waitlist entry — status transitions, notes, quoted wait."""
    result = await db.execute(
        _base_query().where(
            WaitlistEntry.id == entry_id,
            WaitlistEntry.venue_id == venue_id,
        )
    )
    entry = result.unique().scalar_one_or_none()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Waitlist entry not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate status transition if status is being changed
    if "status" in update_data:
        new_status = update_data["status"]
        _validate_transition(entry.status, new_status)

        logger.info("Waitlist %s status: %s -> %s", entry_id, entry.status, new_status)

        # Side effect: seated → record seated_time
        if new_status == "seated":
            entry.seated_time = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(entry, field, value)

    await db.flush()

    result = await db.execute(
        _base_query().where(WaitlistEntry.id == entry.id)
    )
    entry = result.unique().scalar_one()
    return _to_read(entry)


async def seat_from_waitlist(
    db: AsyncSession,
    entry_id: uuid.UUID,
    venue_id: uuid.UUID,
    table_id: uuid.UUID | None = None,
) -> tuple[WaitlistEntryRead, dict | None]:
    """
    Seat a waitlist guest — updates entry to 'seated' and optionally creates
    a walk-in Reservation linked to the assigned table.

    Returns (updated_entry, reservation_dict_or_None).
    """
    result = await db.execute(
        _base_query().where(
            WaitlistEntry.id == entry_id,
            WaitlistEntry.venue_id == venue_id,
        )
    )
    entry = result.unique().scalar_one_or_none()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Waitlist entry not found")

    _validate_transition(entry.status, "seated")
    entry.status = "seated"
    entry.seated_time = datetime.now(timezone.utc)

    reservation_data = None

    if table_id is not None:
        now = datetime.now(timezone.utc)
        reservation = Reservation(
            venue_id=venue_id,
            guest_id=entry.guest_id,
            table_id=table_id,
            party_size=entry.party_size,
            date=now.date(),
            time=now.time(),
            status="seated",
            source="walk_in",
            notes=entry.notes,
            cancel_token=secrets.token_urlsafe(32),
        )
        db.add(reservation)

    # Single flush for both the waitlist status change and the optional
    # reservation insert — keeps them atomic within the same transaction.
    await db.flush()

    if table_id is not None:
        reservation_data = {
            "id": str(reservation.id),
            "status": reservation.status,
            "table_id": str(table_id),
        }

    result = await db.execute(
        _base_query().where(WaitlistEntry.id == entry.id)
    )
    entry = result.unique().scalar_one()
    return _to_read(entry), reservation_data
