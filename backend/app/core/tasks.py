"""
Background task functions executed by the arq worker.

Each function receives a `ctx` dict containing a shared database session factory
(injected via worker startup). Task functions are thin wrappers that load data
and delegate to service-layer functions.

IMPORTANT: All tasks must be async and should handle their own exceptions
gracefully. A failed task should log the error but not crash the worker.
"""

import logging
import uuid as _uuid

logger = logging.getLogger(__name__)


async def send_email_task(
    ctx: dict,
    *,
    to: str,
    subject: str,
    template: str,
    context: dict,
) -> bool:
    """
    Render an email template and send it via SMTP.

    In dev mode (EMAIL_ENABLED=False), the email is rendered but logged
    to stdout instead of sent. This catches template errors early.
    """
    from app.services.email import email_service

    try:
        sent = await email_service.send(
            to=to,
            subject=subject,
            template=template,
            context=context,
        )
        return sent
    except Exception:
        logger.exception("Failed to send email to=%s template=%s", to, template)
        return False


async def daily_reservation_reminders(ctx: dict) -> int:
    """
    Cron job: send reminder emails for tomorrow's reservations.

    Iterates all active venues, converts "tomorrow" into the venue's local
    timezone, and enqueues reminder emails for confirmed/pending reservations.
    Returns the total number of reminders enqueued.
    """
    from datetime import date, datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from app.core.database import async_session_factory
    from app.models.reservation import Reservation
    from app.models.venue import Venue
    from app.services.notifications import send_reservation_reminder

    total_sent = 0

    async with async_session_factory() as db:
        try:
            # Get all active venues
            venues_result = await db.execute(
                select(Venue).where(Venue.is_active.is_(True))
            )
            venues = venues_result.scalars().all()

            for venue in venues:
                try:
                    tz = ZoneInfo(venue.timezone)
                except KeyError:
                    tz = ZoneInfo("UTC")

                # "Tomorrow" in venue's local timezone
                venue_now = datetime.now(tz)
                tomorrow = (venue_now + timedelta(days=1)).date()

                # Find confirmed/pending reservations for tomorrow
                res_result = await db.execute(
                    select(Reservation).where(
                        Reservation.venue_id == venue.id,
                        Reservation.date == tomorrow,
                        Reservation.status.in_(["confirmed", "pending"]),
                    )
                )
                reservations = res_result.scalars().all()

                for reservation in reservations:
                    await send_reservation_reminder(db, reservation)
                    total_sent += 1

            logger.info("Daily reminders: enqueued %d emails", total_sent)
        except Exception:
            logger.exception("Daily reminder cron job failed")

    return total_sent


async def evaluate_auto_tags_task(
    ctx: dict,
    *,
    org_id: str,
    guest_id: str | None = None,
) -> dict:
    """
    Evaluate auto-tag rules for a single guest or all guests in an org.

    Moves the existing synchronous bulk evaluation off the request thread.
    """
    from app.core.database import async_session_factory
    from app.services.auto_tag import evaluate_all_rules, evaluate_rules_for_guest

    parsed_org_id = _uuid.UUID(org_id)
    parsed_guest_id = _uuid.UUID(guest_id) if guest_id else None

    async with async_session_factory() as db:
        try:
            if parsed_guest_id:
                await evaluate_rules_for_guest(db, parsed_guest_id, parsed_org_id)
                await db.commit()
                logger.info("Auto-tag evaluated for guest %s (org=%s)", guest_id, org_id)
                return {"guest_id": guest_id, "status": "ok"}
            else:
                result = await evaluate_all_rules(db, parsed_org_id)
                await db.commit()
                logger.info("Bulk auto-tag evaluated for org %s: %s", org_id, result)
                return {"org_id": org_id, "status": "ok", **result}
        except Exception:
            await db.rollback()
            logger.exception("Auto-tag evaluation failed (org=%s, guest=%s)", org_id, guest_id)
            return {"status": "error"}
