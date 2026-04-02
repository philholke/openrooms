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
from sqlalchemy.orm import joinedload, selectinload

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
from app.services import auto_tag as auto_tag_service
from app.services import notifications as notification_service
from app.services import survey as survey_service

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
            Reservation.status.in_(["pending", "confirmed", "arrived", "partially_arrived", "seated"]),
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

    # 3. Determine initial status — rule must still be active
    rule_result = await db.execute(
        select(AccessRule).where(
            AccessRule.id == data.access_rule_id,
            AccessRule.is_active.is_(True),
            AccessRule.venue_id == venue_id,
        )
    )
    rule = rule_result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Access rule is no longer available",
        )
    initial_status = "pending" if rule.require_deposit else "confirmed"

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

    # ── Email notifications (fire-and-forget) ──
    if initial_status == "confirmed":
        try:
            await notification_service.send_reservation_confirmed(db, reservation)
            await notification_service.send_welcome(db, reservation)
        except Exception:
            logger.warning("Failed to enqueue creation emails", exc_info=True)

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
    from app.models.guest import GuestProfile

    def _apply_filters(stmt):
        nonlocal date, statuses, search
        stmt = stmt.where(Reservation.venue_id == venue_id)
        if date is not None:
            stmt = stmt.where(Reservation.date == date)
        if statuses:
            stmt = stmt.where(Reservation.status.in_(statuses))
        if search:
            # Escape LIKE wildcards to prevent pattern injection
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            stmt = stmt.where(
                Reservation.guest.has(
                    GuestProfile.first_name.ilike(pattern)
                    | GuestProfile.last_name.ilike(pattern)
                )
            )
        return stmt

    # Total count
    count_result = await db.execute(
        _apply_filters(select(func.count(Reservation.id)))
    )
    total = count_result.scalar_one()

    # Paginated query — use selectinload to avoid LIMIT/joinedload interaction
    stmt = _apply_filters(select(Reservation))
    stmt = (
        stmt.options(
            selectinload(Reservation.guest),
            selectinload(Reservation.table),
            selectinload(Reservation.access_rule),
        )
        .order_by(Reservation.time, Reservation.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    reservations = result.scalars().all()

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

    updates = data.model_dump(exclude_unset=True)

    # ── Validate table capacity and venue ownership ──
    # When table_id or party_size changes, ensure the party fits the table
    # and the table belongs to this reservation's venue.
    eff_table_id = updates.get("table_id", reservation.table_id)
    eff_party_size = updates.get("party_size", reservation.party_size)
    if eff_table_id and ("table_id" in updates or "party_size" in updates):
        from app.models.floor_plan import FloorPlan
        table_result = await db.execute(
            select(Table)
            .join(FloorPlan, Table.floor_plan_id == FloorPlan.id)
            .where(
                Table.id == eff_table_id,
                Table.is_active.is_(True),
                FloorPlan.venue_id == venue_id,
            )
        )
        table = table_result.scalar_one_or_none()
        if table is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found in this venue")
        if eff_party_size < table.min_capacity or eff_party_size > table.max_capacity:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Party size {eff_party_size} does not fit table '{table.label}' "
                f"(capacity {table.min_capacity}–{table.max_capacity})",
            )

    # If party_size is changing, re-validate against the slot's capacity limit.
    # Lock sibling reservations in the same slot to prevent concurrent
    # party_size increases from both passing the capacity check.
    if "party_size" in updates and updates["party_size"] != reservation.party_size:
        new_size = updates["party_size"]
        if reservation.access_rule_id:
            rule_result = await db.execute(
                select(AccessRule).where(AccessRule.id == reservation.access_rule_id)
            )
            rule = rule_result.scalar_one_or_none()
            if rule and rule.max_covers_per_slot is not None:
                # Lock + count other reservations in the same slot (excluding this one)
                other_covers_result = await db.execute(
                    select(func.coalesce(func.sum(Reservation.party_size), 0)).where(
                        Reservation.venue_id == venue_id,
                        Reservation.date == reservation.date,
                        Reservation.time == reservation.time,
                        Reservation.access_rule_id == reservation.access_rule_id,
                        Reservation.id != reservation.id,
                        Reservation.status.in_(
                            ["pending", "confirmed", "arrived", "partially_arrived", "seated"]
                        ),
                    ).with_for_update()
                )
                other_covers = other_covers_result.scalar_one()
                if other_covers + new_size > rule.max_covers_per_slot:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        f"New party size ({new_size}) would exceed slot capacity "
                        f"({rule.max_covers_per_slot} covers, {other_covers} already booked)",
                    )

    for field, value in updates.items():
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
    # Lock + read in a single query to prevent concurrent status transitions
    # and eliminate the gap between lock acquisition and data read.
    result = await db.execute(
        _base_query().where(
            Reservation.id == reservation_id,
            Reservation.venue_id == venue_id,
        ).with_for_update()
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
        await db.flush()  # Flush visit so auto-tag rules see current data

        # Non-critical side effects: failures here must not roll back the
        # reservation status change or the guest visit record.
        dispatch = None
        try:
            dispatch = await survey_service.generate_survey_dispatch(
                db,
                venue_id=reservation.venue_id,
                reservation_id=reservation.id,
                guest_id=reservation.guest_id,
            )
        except Exception:
            logger.exception(
                "Failed to generate survey dispatch for reservation %s",
                reservation.id,
            )

        if dispatch:
            try:
                await notification_service.send_survey_invite(
                    db, dispatch, reservation,
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue survey invite for reservation %s",
                    reservation.id,
                )

        try:
            from app.models.venue import Venue
            venue_result = await db.execute(
                select(Venue.org_id).where(Venue.id == reservation.venue_id)
            )
            org_id = venue_result.scalar_one()
            await auto_tag_service.evaluate_rules_for_guest(
                db, reservation.guest_id, org_id,
            )
        except Exception:
            logger.exception(
                "Failed to evaluate auto-tag rules for guest %s",
                reservation.guest_id,
            )

    if new_status == "cancelled":
        reservation.cancelled_at = datetime.now(timezone.utc)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        _base_query().where(Reservation.id == reservation.id)
    )
    reservation = result.unique().scalar_one()

    if new_status == "cancelled":
        try:
            await notification_service.send_reservation_cancelled(db, reservation)
        except Exception:
            logger.warning("Failed to enqueue cancellation email", exc_info=True)

    return _to_read(reservation)


async def cancel_reservation(
    db: AsyncSession,
    reservation_id: uuid.UUID,
    venue_id: uuid.UUID,
    reason: str | None = None,
) -> ReservationRead:
    """Cancel a reservation — convenience wrapper around update_status."""
    # Lock + read in a single query to prevent concurrent cancel/status races.
    result = await db.execute(
        _base_query().where(
            Reservation.id == reservation_id,
            Reservation.venue_id == venue_id,
        ).with_for_update()
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

    try:
        await notification_service.send_reservation_cancelled(db, reservation)
    except Exception:
        logger.warning("Failed to enqueue cancellation email", exc_info=True)

    return _to_read(reservation)
