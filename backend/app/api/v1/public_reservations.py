"""
Public reservation endpoints — unauthenticated, token-based access.

Used by the guest self-service cancellation page.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import async_session_factory
from app.core.limiter import limiter
from app.models.guest import GuestProfile
from app.models.reservation import Reservation
from app.models.venue import Venue
from app.services.reservation import validate_transition
from app.services import notifications as notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/reservations", tags=["public-reservations"])


class PublicReservationInfo(BaseModel):
    """Public-safe reservation summary for the cancellation page."""

    venue_name: str
    venue_address: str | None
    guest_first_name: str | None
    reservation_date: str
    reservation_time: str
    party_size: int
    status: str
    special_requests: str | None
    cancellation_policy_hours: int | None


class CancelResult(BaseModel):
    message: str


@router.get("/{cancel_token}", response_model=PublicReservationInfo)
@limiter.limit("30/minute")
async def get_reservation_by_token(request: Request, cancel_token: str):
    """Fetch reservation summary for the self-service cancellation page."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Reservation)
            .options(joinedload(Reservation.guest), joinedload(Reservation.access_rule))
            .where(Reservation.cancel_token == cancel_token)
        )
        reservation = result.unique().scalar_one_or_none()

        if reservation is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Reservation not found or link has expired",
            )

        # Load venue
        venue_result = await db.execute(
            select(Venue).where(Venue.id == reservation.venue_id)
        )
        venue = venue_result.scalar_one()

        cancellation_policy_hours = None
        if reservation.access_rule:
            cancellation_policy_hours = reservation.access_rule.cancellation_policy_hours

        return PublicReservationInfo(
            venue_name=venue.name,
            venue_address=venue.address,
            guest_first_name=reservation.guest.first_name if reservation.guest else None,
            reservation_date=reservation.date.strftime("%A, %B %-d, %Y"),
            reservation_time=reservation.time.strftime("%-I:%M %p"),
            party_size=reservation.party_size,
            status=reservation.status,
            special_requests=reservation.special_requests,
            cancellation_policy_hours=cancellation_policy_hours,
        )


@router.post("/{cancel_token}/cancel", response_model=CancelResult)
@limiter.limit("5/minute")
async def cancel_reservation_by_token(request: Request, cancel_token: str):
    """Cancel a reservation using the guest's cancel token."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Reservation)
                .where(Reservation.cancel_token == cancel_token)
                .with_for_update()
            )
            reservation = result.scalar_one_or_none()

            if reservation is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    "Reservation not found or link has expired",
                )

            if reservation.status in ("cancelled", "completed", "no_show"):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Reservation is already {reservation.status}",
                )

            validate_transition(reservation.status, "cancelled")

            reservation.status = "cancelled"
            reservation.cancelled_at = datetime.now(timezone.utc)
            existing_notes = reservation.notes or ""
            reservation.notes = f"{existing_notes}\n[Self-service cancellation]".strip()

            await db.flush()

            try:
                await notification_service.send_reservation_cancelled(db, reservation)
            except Exception:
                logger.warning("Failed to enqueue cancel email", exc_info=True)

            await db.commit()

            logger.info("Reservation %s cancelled via token", reservation.id)
            return CancelResult(message="Reservation cancelled successfully")

        except HTTPException:
            raise
        except Exception:
            await db.rollback()
            logger.warning("Failed to cancel reservation via token")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Failed to cancel reservation",
            )
