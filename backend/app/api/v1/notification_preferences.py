import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.models.venue import Venue
from app.schemas.envelope import Envelope, ok
from app.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from app.services.notification_preference import get_preferences, update_preferences

router = APIRouter(tags=["notification-preferences"])


async def _verify_venue_org(db: AsyncSession, venue_id: uuid.UUID, org_id: uuid.UUID) -> None:
    """Verify the venue belongs to the requesting user's organization."""
    result = await db.execute(
        select(Venue.id).where(
            Venue.id == venue_id,
            Venue.org_id == org_id,
            Venue.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")


@router.get(
    "/venues/{venue_id}/notification-preferences",
    response_model=Envelope[list[NotificationPreferenceRead]],
)
async def list_notification_preferences(
    venue_id: uuid.UUID,
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_venue_org(db, venue_id, org.id)
    return ok(await get_preferences(db, venue_id))


@router.patch(
    "/venues/{venue_id}/notification-preferences",
    response_model=Envelope[list[NotificationPreferenceRead]],
)
async def update_notification_preferences(
    venue_id: uuid.UUID,
    body: list[NotificationPreferenceUpdate],
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _verify_venue_org(db, venue_id, org.id)
    return ok(await update_preferences(db, venue_id, body))
