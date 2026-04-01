"""
Auto-tag evaluation engine.

Rules are stored as JSONB conditions on AutoTagRule, linked 1:1 to a Tag
where is_auto=true. Evaluation checks each rule's conditions against a
guest's data and applies or removes the tag accordingly.

Two entry points:
- evaluate_rules_for_guest() — single guest, called on reservation
  completion and survey submission (wired in Phase 4H).
- evaluate_all_rules() — bulk evaluation for all guests in an org,
  triggered manually by admins for backfill.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auto_tag_rule import AutoTagRule
from app.models.guest import GuestProfile, GuestVisit, guest_tags
from app.models.survey import Survey
from app.models.tag import Tag
from app.schemas.auto_tag_rule import AutoTagConditions, BulkEvaluateResult

logger = logging.getLogger(__name__)


async def _get_guest_stats(
    db: AsyncSession,
    guest_id: uuid.UUID,
    venue_id: uuid.UUID | None = None,
) -> dict:
    """
    Gather all data needed for condition evaluation in minimal queries.

    Returns a dict with:
      - visit_count: int
      - last_visit_date: datetime | None
      - total_spend: int (cents)
      - avg_rating: float | None
      - tag_names: set[str]
    """
    # Visit stats (optionally scoped to venue)
    visit_query = select(
        func.count().label("visit_count"),
        func.max(GuestVisit.visited_at).label("last_visit_date"),
        func.coalesce(func.sum(GuestVisit.spend_amount), Decimal(0)).label("total_spend"),
    ).where(GuestVisit.guest_id == guest_id)

    if venue_id is not None:
        visit_query = visit_query.where(GuestVisit.venue_id == venue_id)

    visit_result = await db.execute(visit_query)
    visit_row = visit_result.one()

    # Average survey rating
    rating_result = await db.execute(
        select(func.avg(Survey.overall_rating)).where(Survey.guest_id == guest_id)
    )
    avg_rating = rating_result.scalar_one_or_none()

    # Current tag names
    tag_result = await db.execute(
        select(Tag.name)
        .join(guest_tags, Tag.id == guest_tags.c.tag_id)
        .where(guest_tags.c.guest_id == guest_id)
    )
    tag_names = {row[0] for row in tag_result.all()}

    return {
        "visit_count": visit_row.visit_count,
        "last_visit_date": visit_row.last_visit_date,
        "total_spend": int(visit_row.total_spend * 100),  # Convert to cents
        "avg_rating": float(avg_rating) if avg_rating is not None else None,
        "tag_names": tag_names,
    }


def _check_conditions(
    conditions: AutoTagConditions,
    stats: dict,
) -> bool:
    """
    Evaluate all specified conditions against guest stats.
    All conditions are AND-combined — all must pass for a match.
    """
    now = datetime.now(timezone.utc)

    if conditions.visit_count_gte is not None:
        if stats["visit_count"] < conditions.visit_count_gte:
            return False

    if conditions.visit_count_lte is not None:
        if stats["visit_count"] > conditions.visit_count_lte:
            return False

    if conditions.last_visit_within_days is not None:
        if stats["last_visit_date"] is None:
            return False
        cutoff = now - timedelta(days=conditions.last_visit_within_days)
        if stats["last_visit_date"] < cutoff:
            return False

    if conditions.last_visit_not_within_days is not None:
        if stats["last_visit_date"] is not None:
            cutoff = now - timedelta(days=conditions.last_visit_not_within_days)
            if stats["last_visit_date"] >= cutoff:
                return False
        # No visits at all counts as "not visited within N days" — passes

    if conditions.total_spend_gte is not None:
        if stats["total_spend"] < conditions.total_spend_gte:
            return False

    if conditions.avg_rating_gte is not None:
        if stats["avg_rating"] is None:
            return False
        if stats["avg_rating"] < conditions.avg_rating_gte:
            return False

    if conditions.avg_rating_lte is not None:
        if stats["avg_rating"] is None:
            return False
        if stats["avg_rating"] > conditions.avg_rating_lte:
            return False

    if conditions.has_tag is not None:
        if conditions.has_tag not in stats["tag_names"]:
            return False

    if conditions.not_has_tag is not None:
        if conditions.not_has_tag in stats["tag_names"]:
            return False

    return True


async def _apply_tag(
    db: AsyncSession,
    guest_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> bool:
    """Apply a tag to a guest. Returns True if newly applied, False if already present."""
    try:
        async with db.begin_nested():
            await db.execute(
                guest_tags.insert().values(guest_id=guest_id, tag_id=tag_id)
            )
        return True
    except IntegrityError:
        return False


async def _remove_tag(
    db: AsyncSession,
    guest_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> bool:
    """Remove a tag from a guest. Returns True if removed, False if not present."""
    result = await db.execute(
        delete(guest_tags).where(
            guest_tags.c.guest_id == guest_id,
            guest_tags.c.tag_id == tag_id,
        )
    )
    return result.rowcount > 0


async def evaluate_rules_for_guest(
    db: AsyncSession,
    guest_id: uuid.UUID,
    org_id: uuid.UUID,
) -> tuple[int, int]:
    """
    Run all active auto-tag rules for a single guest.

    Returns (tags_applied, tags_removed).
    """
    # Load all active rules for this org
    rules_result = await db.execute(
        select(AutoTagRule).where(
            AutoTagRule.org_id == org_id,
            AutoTagRule.is_active.is_(True),
        )
    )
    rules = rules_result.scalars().all()

    if not rules:
        return 0, 0

    # Gather stats once for the guest (without venue scope first)
    stats = await _get_guest_stats(db, guest_id)
    applied = 0
    removed = 0

    for rule in rules:
        conditions = AutoTagConditions.model_validate(rule.conditions)

        # If rule has venue_id scope, re-gather venue-specific stats
        if conditions.venue_id is not None:
            rule_stats = await _get_guest_stats(db, guest_id, venue_id=conditions.venue_id)
        else:
            rule_stats = stats

        matches = _check_conditions(conditions, rule_stats)

        if matches:
            if await _apply_tag(db, guest_id, rule.tag_id):
                applied += 1
        else:
            if await _remove_tag(db, guest_id, rule.tag_id):
                removed += 1

    if applied or removed:
        logger.info(
            "Auto-tag evaluation for guest %s: applied=%d removed=%d",
            guest_id, applied, removed,
        )

    return applied, removed


_BATCH_SIZE = 500


async def evaluate_all_rules(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> BulkEvaluateResult:
    """
    Run all active auto-tag rules against every guest in the org.
    Used for backfill after creating new rules. Processes guests in
    batches to avoid unbounded query volume and long-held transactions.
    """
    # Load all active rules
    rules_result = await db.execute(
        select(AutoTagRule).where(
            AutoTagRule.org_id == org_id,
            AutoTagRule.is_active.is_(True),
        )
    )
    rules = rules_result.scalars().all()

    if not rules:
        return BulkEvaluateResult(guests_evaluated=0, tags_applied=0, tags_removed=0)

    # Load all guest IDs in this org
    guests_result = await db.execute(
        select(GuestProfile.id).where(GuestProfile.org_id == org_id)
    )
    guest_ids = [row[0] for row in guests_result.all()]

    total_applied = 0
    total_removed = 0

    for i in range(0, len(guest_ids), _BATCH_SIZE):
        batch = guest_ids[i : i + _BATCH_SIZE]
        for guest_id in batch:
            applied, removed = await evaluate_rules_for_guest(db, guest_id, org_id)
            total_applied += applied
            total_removed += removed
        # Flush after each batch to persist progress and release row locks
        await db.flush()

    logger.info(
        "Bulk auto-tag evaluation for org %s: guests=%d applied=%d removed=%d",
        org_id, len(guest_ids), total_applied, total_removed,
    )

    return BulkEvaluateResult(
        guests_evaluated=len(guest_ids),
        tags_applied=total_applied,
        tags_removed=total_removed,
    )
