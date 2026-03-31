import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, get_current_user, require_role
from app.models.organization import Organization
from app.models.user import User
from app.models.venue import Venue
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.reservation import (
    ReservationCancel,
    ReservationCreate,
    ReservationRead,
    ReservationStatusUpdate,
    ReservationUpdate,
)
from app.services import reservation as reservation_service
from app.api.v1.venues import _get_venue_or_404

router = APIRouter(tags=["reservations"])


# ─── Helpers ─────────────────────────────────────────────────────────────

async def _get_venue_public(db: AsyncSession, venue_id: uuid.UUID) -> Venue:
    """Look up a venue without auth — for public booking endpoints."""
    result = await db.execute(
        select(Venue).where(Venue.id == venue_id, Venue.is_active.is_(True))
    )
    venue = result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")
    return venue


# ─── Venue-scoped routes ─────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/reservations",
    response_model=PaginatedEnvelope[ReservationRead],
)
async def list_reservations(
    venue_id: uuid.UUID,
    date: date = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status_filter: str = Query(
        None,
        alias="status",
        description="Comma-separated statuses: confirmed,arrived",
    ),
    search: str = Query(None, description="Search guest first/last name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)

    statuses = None
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]

    items, total = await reservation_service.list_reservations(
        db,
        venue_id,
        date=date,
        statuses=statuses,
        search=search,
        page=page,
        per_page=per_page,
    )
    return paginated(items, page=page, per_page=per_page, total=total)


@router.post(
    "/venues/{venue_id}/reservations",
    response_model=Envelope[ReservationRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    venue_id: uuid.UUID,
    body: ReservationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — creates a reservation (booking widget or staff).
    No auth required for the widget flow; guest profile is created server-side.
    """
    venue = await _get_venue_public(db, venue_id)

    reservation = await reservation_service.create_reservation(
        db,
        venue_id=venue_id,
        org_id=venue.org_id,
        data=body,
        venue_timezone=venue.timezone,
    )
    return ok(reservation)


# ─── Direct reservation routes ───────────────────────────────────────────

@router.get(
    "/reservations/{reservation_id}",
    response_model=Envelope[ReservationRead],
)
async def get_reservation(
    reservation_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    # Find the reservation and verify it belongs to a venue in this org
    from app.models.reservation import Reservation
    result = await db.execute(
        select(Reservation.venue_id).where(Reservation.id == reservation_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    await _get_venue_or_404(db, row.venue_id, org.id)

    reservation = await reservation_service.get_reservation(
        db, reservation_id, row.venue_id
    )
    return ok(reservation)


@router.patch(
    "/reservations/{reservation_id}",
    response_model=Envelope[ReservationRead],
)
async def update_reservation(
    reservation_id: uuid.UUID,
    body: ReservationUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.reservation import Reservation
    result = await db.execute(
        select(Reservation.venue_id).where(Reservation.id == reservation_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    await _get_venue_or_404(db, row.venue_id, org.id)

    reservation = await reservation_service.update_reservation(
        db, reservation_id, row.venue_id, body
    )
    return ok(reservation)


@router.patch(
    "/reservations/{reservation_id}/status",
    response_model=Envelope[ReservationRead],
)
async def update_reservation_status(
    reservation_id: uuid.UUID,
    body: ReservationStatusUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.reservation import Reservation
    result = await db.execute(
        select(Reservation.venue_id).where(Reservation.id == reservation_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    await _get_venue_or_404(db, row.venue_id, org.id)

    reservation = await reservation_service.update_status(
        db, reservation_id, row.venue_id, body.status
    )
    return ok(reservation)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=Envelope[ReservationRead],
)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    body: ReservationCancel = ReservationCancel(),
    token: str = Query(None, description="Cancel token from confirmation email"),
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — allows both guests (via widget) and staff to cancel.
    Requires a valid cancel_token (sent in confirmation email) to prevent
    unauthorized cancellation by UUID guessing.
    """
    from app.models.reservation import Reservation

    if token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Cancel token is required. Use the link from your confirmation email.",
        )

    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.cancel_token == token,
        )
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found or invalid token")

    cancelled = await reservation_service.cancel_reservation(
        db, reservation_id, reservation.venue_id, body.reason
    )
    return ok(cancelled)
