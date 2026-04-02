"""
Notification service — builds email contexts from domain objects and
enqueues send_email_task via the background task system.

All functions are fire-and-forget: they catch exceptions internally
so callers (reservation service, survey service) are never blocked.
"""

import logging
import uuid
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import enqueue
from app.models.guest import GuestProfile
from app.models.reservation import Reservation
from app.models.survey import SurveyDispatch
from app.models.venue import Venue
from app.services.notification_preference import is_notification_enabled

logger = logging.getLogger(__name__)


def _format_date(d: date) -> str:
    """Format date for guest-facing display: 'Saturday, April 5, 2026'."""
    return d.strftime("%A, %B %-d, %Y")


def _format_time(t: time) -> str:
    """Format time for guest-facing display: '7:30 PM'."""
    return t.strftime("%-I:%M %p")


async def _load_venue(db: AsyncSession, venue_id: uuid.UUID) -> Venue | None:
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    return result.scalar_one_or_none()


async def _load_guest(db: AsyncSession, guest_id: uuid.UUID) -> GuestProfile | None:
    result = await db.execute(select(GuestProfile).where(GuestProfile.id == guest_id))
    return result.scalar_one_or_none()


def _venue_context(venue: Venue) -> dict:
    """Common venue fields for all email templates."""
    return {
        "venue_name": venue.name,
        "venue_address": venue.address or "",
        "booking_url": f"{settings.APP_BASE_URL}/book/{venue.id}",
    }


def _reservation_context(reservation: Reservation) -> dict:
    """Common reservation fields for email templates."""
    ctx = {
        "reservation_date": _format_date(reservation.date),
        "reservation_time": _format_time(reservation.time),
        "party_size": reservation.party_size,
        "special_requests": reservation.special_requests or "",
    }
    if reservation.cancel_token:
        ctx["cancel_url"] = (
            f"{settings.APP_BASE_URL}/cancel/{reservation.cancel_token}"
        )
    return ctx


async def send_reservation_confirmed(
    db: AsyncSession,
    reservation: Reservation,
) -> None:
    """Enqueue confirmation email after reservation creation."""
    try:
        if not await is_notification_enabled(db, reservation.venue_id, "reservation_confirmed"):
            return

        guest = await _load_guest(db, reservation.guest_id)
        venue = await _load_venue(db, reservation.venue_id)
        if not guest or not venue or not guest.email:
            return

        context = {
            "guest_first_name": guest.first_name or "",
            **_venue_context(venue),
            **_reservation_context(reservation),
        }

        await enqueue(
            "send_email_task",
            to=guest.email,
            subject=f"Reservation Confirmed — {venue.name}",
            template="reservation_confirmed",
            context=context,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue confirmation email for reservation %s",
            reservation.id,
            exc_info=True,
        )


async def send_reservation_cancelled(
    db: AsyncSession,
    reservation: Reservation,
) -> None:
    """Enqueue cancellation acknowledgement email."""
    try:
        if not await is_notification_enabled(db, reservation.venue_id, "cancellation_ack"):
            return

        guest = await _load_guest(db, reservation.guest_id)
        venue = await _load_venue(db, reservation.venue_id)
        if not guest or not venue or not guest.email:
            return

        context = {
            "guest_first_name": guest.first_name or "",
            **_venue_context(venue),
            **_reservation_context(reservation),
        }

        await enqueue(
            "send_email_task",
            to=guest.email,
            subject=f"Reservation Cancelled — {venue.name}",
            template="reservation_cancelled",
            context=context,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue cancellation email for reservation %s",
            reservation.id,
            exc_info=True,
        )


async def send_survey_invite(
    db: AsyncSession,
    dispatch: SurveyDispatch,
    reservation: Reservation,
) -> None:
    """Enqueue survey invite email after reservation completion."""
    try:
        if not await is_notification_enabled(db, reservation.venue_id, "survey_invite"):
            return

        guest = await _load_guest(db, reservation.guest_id)
        venue = await _load_venue(db, reservation.venue_id)
        if not guest or not venue or not guest.email:
            return

        context = {
            "guest_first_name": guest.first_name or "",
            "reservation_date": _format_date(reservation.date),
            "survey_url": f"{settings.APP_BASE_URL}/survey/{dispatch.token}",
            **_venue_context(venue),
        }

        await enqueue(
            "send_email_task",
            to=guest.email,
            subject=f"How was your visit to {venue.name}?",
            template="survey_invite",
            context=context,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue survey invite for dispatch %s",
            dispatch.id,
            exc_info=True,
        )


async def send_welcome(
    db: AsyncSession,
    reservation: Reservation,
) -> None:
    """Enqueue welcome email for first-time guests."""
    try:
        guest = await _load_guest(db, reservation.guest_id)
        venue = await _load_venue(db, reservation.venue_id)
        if not guest or not venue or not guest.email:
            return

        # Check if this is truly the guest's first reservation in the org
        from app.models.guest import GuestVisit
        from sqlalchemy import func

        visit_count_result = await db.execute(
            select(func.count(GuestVisit.id)).where(
                GuestVisit.guest_id == guest.id
            )
        )
        if visit_count_result.scalar_one() > 0:
            return  # Not a first-timer

        context = {
            "guest_first_name": guest.first_name or "",
            **_venue_context(venue),
            **_reservation_context(reservation),
        }

        await enqueue(
            "send_email_task",
            to=guest.email,
            subject=f"Welcome to {venue.name}!",
            template="welcome",
            context=context,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue welcome email for reservation %s",
            reservation.id,
            exc_info=True,
        )


async def send_reservation_reminder(
    db: AsyncSession,
    reservation: Reservation,
) -> None:
    """Enqueue reminder email (called by daily cron job)."""
    try:
        if not await is_notification_enabled(db, reservation.venue_id, "reservation_reminder"):
            return

        guest = await _load_guest(db, reservation.guest_id)
        venue = await _load_venue(db, reservation.venue_id)
        if not guest or not venue or not guest.email:
            return

        context = {
            "guest_first_name": guest.first_name or "",
            **_venue_context(venue),
            **_reservation_context(reservation),
        }

        await enqueue(
            "send_email_task",
            to=guest.email,
            subject=f"Reminder: Reservation Tomorrow at {venue.name}",
            template="reservation_reminder",
            context=context,
        )
    except Exception:
        logger.warning(
            "Failed to enqueue reminder email for reservation %s",
            reservation.id,
            exc_info=True,
        )
