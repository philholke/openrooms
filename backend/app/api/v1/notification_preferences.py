import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from app.services.notification_preference import get_preferences, update_preferences

router = APIRouter(tags=["notification-preferences"])


@router.get(
    "/venues/{venue_id}/notification-preferences",
    response_model=list[NotificationPreferenceRead],
)
async def list_notification_preferences(
    venue_id: uuid.UUID,
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    return await get_preferences(db, venue_id)


@router.patch(
    "/venues/{venue_id}/notification-preferences",
    response_model=list[NotificationPreferenceRead],
)
async def update_notification_preferences(
    venue_id: uuid.UUID,
    body: list[NotificationPreferenceUpdate],
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    return await update_preferences(db, venue_id, body)
