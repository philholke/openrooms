"""
Notification preference service — manages per-venue notification toggles.

Preferences are created lazily: if no row exists for a venue+type pair,
the notification is considered enabled (default).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preference import NotificationPreference
from app.schemas.notification_preference import (
    NOTIFICATION_TYPES,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)


async def get_preferences(
    db: AsyncSession,
    venue_id: uuid.UUID,
) -> list[NotificationPreferenceRead]:
    """Return all notification preferences for a venue, filling in defaults."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.venue_id == venue_id,
        )
    )
    existing = {p.notification_type: p for p in result.scalars().all()}

    prefs = []
    for ntype in NOTIFICATION_TYPES:
        if ntype in existing:
            prefs.append(NotificationPreferenceRead.model_validate(existing[ntype]))
        else:
            # Default: enabled
            prefs.append(NotificationPreferenceRead(
                id=uuid.uuid4(),  # placeholder UUID for the response
                venue_id=venue_id,
                notification_type=ntype,
                enabled=True,
            ))
    return prefs


async def update_preferences(
    db: AsyncSession,
    venue_id: uuid.UUID,
    updates: list[NotificationPreferenceUpdate],
) -> list[NotificationPreferenceRead]:
    """Upsert notification preferences for a venue."""
    for update in updates:
        if update.notification_type not in NOTIFICATION_TYPES:
            continue

        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.venue_id == venue_id,
                NotificationPreference.notification_type == update.notification_type,
            )
        )
        pref = result.scalar_one_or_none()

        if pref:
            pref.enabled = update.enabled
        else:
            pref = NotificationPreference(
                venue_id=venue_id,
                notification_type=update.notification_type,
                enabled=update.enabled,
            )
            db.add(pref)

    await db.flush()
    return await get_preferences(db, venue_id)


async def is_notification_enabled(
    db: AsyncSession,
    venue_id: uuid.UUID,
    notification_type: str,
) -> bool:
    """Check if a specific notification type is enabled for a venue."""
    result = await db.execute(
        select(NotificationPreference.enabled).where(
            NotificationPreference.venue_id == venue_id,
            NotificationPreference.notification_type == notification_type,
        )
    )
    enabled = result.scalar_one_or_none()
    # Default to True if no preference row exists
    return enabled if enabled is not None else True
