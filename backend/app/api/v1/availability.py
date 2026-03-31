import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.venue import Venue
from app.schemas.availability import AvailabilityResponse
from app.schemas.envelope import Envelope, ok
from app.services.availability import get_available_slots

router = APIRouter(tags=["availability"])


@router.get(
    "/venues/{venue_id}/availability",
    response_model=Envelope[AvailabilityResponse],
)
async def check_availability(
    venue_id: uuid.UUID,
    date: date = Query(..., description="Target date (YYYY-MM-DD)"),
    party_size: int = Query(2, ge=1, le=20, description="Number of guests"),
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — returns available time slots for the given venue, date,
    and party size. No authentication required (used by the booking widget).
    """
    result = await db.execute(
        select(Venue).where(Venue.id == venue_id, Venue.is_active.is_(True))
    )
    venue = result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")

    slots = await get_available_slots(
        db,
        venue_id,
        target_date=date,
        party_size=party_size,
        venue_timezone=venue.timezone,
    )

    return ok(
        AvailabilityResponse(
            venue_id=venue_id,
            date=date,
            party_size=party_size,
            slots=slots,
        )
    )
