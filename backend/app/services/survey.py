"""
Survey service — CRUD for post-visit feedback surveys.

Phase 4D extends this with:
- generate_survey_dispatch() — creates a token-based survey link
- get_dispatch_info() — returns public info for a survey token
- submit_public_survey() — guest submits via token, no auth
- get_survey_stats() — aggregated ratings for a venue
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import GuestProfile
from app.models.reservation import Reservation
from app.models.survey import Survey, SurveyDispatch
from app.models.venue import Venue
from app.schemas.survey import (
    RatingDistribution,
    SurveyCreate,
    SurveyPublicInfo,
    SurveyPublicSubmit,
    SurveyRead,
    SurveyStats,
)

logger = logging.getLogger(__name__)


async def create_survey(
    db: AsyncSession,
    data: SurveyCreate,
    org_id: uuid.UUID,
) -> SurveyRead:
    """Create a survey response, validating cross-tenant references."""
    # Verify venue belongs to the same org
    venue_result = await db.execute(
        select(Venue.id).where(
            Venue.id == data.venue_id,
            Venue.org_id == org_id,
            Venue.is_active.is_(True),
        )
    )
    if venue_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found in this organization")

    # Verify guest belongs to the same org
    guest_result = await db.execute(
        select(GuestProfile.id).where(
            GuestProfile.id == data.guest_id,
            GuestProfile.org_id == org_id,
        )
    )
    if guest_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found in this organization")

    # Verify reservation belongs to the same venue (if provided)
    if data.reservation_id is not None:
        res_result = await db.execute(
            select(Reservation.id).where(
                Reservation.id == data.reservation_id,
                Reservation.venue_id == data.venue_id,
            )
        )
        if res_result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found for this venue")

    survey = Survey(**data.model_dump())
    db.add(survey)
    await db.flush()
    await db.refresh(survey)

    logger.info(
        "Survey created: id=%s venue=%s guest=%s rating=%d",
        survey.id, data.venue_id, data.guest_id, data.overall_rating,
    )
    return SurveyRead.model_validate(survey)


async def list_surveys(
    db: AsyncSession,
    venue_id: uuid.UUID,
    *,
    guest_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[SurveyRead], int]:
    """List surveys for a venue with optional guest filter."""
    base = select(Survey).where(Survey.venue_id == venue_id)
    if guest_id:
        base = base.where(Survey.guest_id == guest_id)

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(Survey.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    surveys = result.scalars().all()

    return [SurveyRead.model_validate(s) for s in surveys], total


async def get_survey(
    db: AsyncSession,
    survey_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
) -> SurveyRead:
    """Get a single survey by ID, with optional org-scope enforcement."""
    stmt = select(Survey).where(Survey.id == survey_id)
    if org_id is not None:
        stmt = stmt.join(Venue, Survey.venue_id == Venue.id).where(
            Venue.org_id == org_id
        )
    result = await db.execute(stmt)
    survey = result.scalar_one_or_none()
    if survey is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")
    return SurveyRead.model_validate(survey)


# ─── Public survey dispatch (Phase 4D) ───────────────────────────────────


async def generate_survey_dispatch(
    db: AsyncSession,
    venue_id: uuid.UUID,
    reservation_id: uuid.UUID,
    guest_id: uuid.UUID,
) -> SurveyDispatch:
    """
    Create a token-based survey dispatch for a completed reservation.
    Called from reservation completion flow (Phase 4H wiring).
    """
    token = secrets.token_urlsafe(32)

    dispatch = SurveyDispatch(
        venue_id=venue_id,
        reservation_id=reservation_id,
        guest_id=guest_id,
        token=token,
    )
    db.add(dispatch)
    await db.flush()
    await db.refresh(dispatch)

    logger.info(
        "Survey dispatch created: id=%s venue=%s reservation=%s token=%s...",
        dispatch.id, venue_id, reservation_id, token[:8],
    )
    return dispatch


async def get_dispatch_info(
    db: AsyncSession,
    token: str,
) -> SurveyPublicInfo:
    """
    Look up a survey dispatch by token and return public-safe info
    for rendering the survey form. 404 if invalid or already submitted.
    """
    result = await db.execute(
        select(SurveyDispatch)
        .where(
            SurveyDispatch.token == token,
            SurveyDispatch.submitted_at.is_(None),
        )
    )
    dispatch = result.scalar_one_or_none()
    if dispatch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found or already submitted")

    # Fetch venue name, guest first name, reservation date
    venue_result = await db.execute(select(Venue.name).where(Venue.id == dispatch.venue_id))
    venue_name = venue_result.scalar_one()

    guest_result = await db.execute(
        select(GuestProfile.first_name).where(GuestProfile.id == dispatch.guest_id)
    )
    guest_first_name = guest_result.scalar_one()

    res_result = await db.execute(
        select(Reservation.date).where(Reservation.id == dispatch.reservation_id)
    )
    reservation_date = res_result.scalar_one()

    return SurveyPublicInfo(
        venue_name=venue_name,
        guest_first_name=guest_first_name,
        reservation_date=reservation_date,
    )


async def submit_public_survey(
    db: AsyncSession,
    token: str,
    data: SurveyPublicSubmit,
) -> SurveyRead:
    """
    Submit a survey via public token. Creates the Survey, links it to the
    dispatch, and marks the dispatch as submitted.
    """
    result = await db.execute(
        select(SurveyDispatch)
        .where(
            SurveyDispatch.token == token,
            SurveyDispatch.submitted_at.is_(None),
        )
        .with_for_update()
    )
    dispatch = result.scalar_one_or_none()
    if dispatch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found or already submitted")

    # Create the survey
    survey = Survey(
        venue_id=dispatch.venue_id,
        reservation_id=dispatch.reservation_id,
        guest_id=dispatch.guest_id,
        overall_rating=data.overall_rating,
        food_rating=data.food_rating,
        service_rating=data.service_rating,
        ambiance_rating=data.ambiance_rating,
        drinks_rating=data.drinks_rating,
        comment=data.comment,
    )
    db.add(survey)
    await db.flush()

    # Link and mark dispatch as submitted
    dispatch.survey_id = survey.id
    dispatch.submitted_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(survey)

    logger.info(
        "Public survey submitted: id=%s venue=%s guest=%s rating=%d",
        survey.id, dispatch.venue_id, dispatch.guest_id, data.overall_rating,
    )

    # Evaluate auto-tag rules (rating-based rules can fire immediately)
    from app.services import auto_tag as auto_tag_service
    venue_result = await db.execute(
        select(Venue.org_id).where(Venue.id == dispatch.venue_id)
    )
    org_id = venue_result.scalar_one()
    await auto_tag_service.evaluate_rules_for_guest(db, dispatch.guest_id, org_id)

    return SurveyRead.model_validate(survey)


async def get_survey_stats(
    db: AsyncSession,
    venue_id: uuid.UUID,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> SurveyStats:
    """Aggregated survey statistics for a venue with optional date range."""
    base = select(Survey).where(Survey.venue_id == venue_id)
    if date_from is not None:
        base = base.where(Survey.created_at >= date_from)
    if date_to is not None:
        base = base.where(Survey.created_at <= date_to)

    # Averages and total count
    agg_result = await db.execute(
        select(
            func.count().label("total"),
            func.avg(Survey.overall_rating).label("avg_overall"),
            func.avg(Survey.food_rating).label("avg_food"),
            func.avg(Survey.service_rating).label("avg_service"),
            func.avg(Survey.ambiance_rating).label("avg_ambiance"),
            func.avg(Survey.drinks_rating).label("avg_drinks"),
        ).select_from(base.subquery())
    )
    agg = agg_result.one()

    # Rating distribution (1-5) — reuse base subquery for consistency
    dist_result = await db.execute(
        select(
            Survey.overall_rating.label("rating"),
            func.count().label("count"),
        )
        .select_from(base.subquery())
        .group_by(Survey.overall_rating)
        .order_by(Survey.overall_rating)
    )
    dist_rows = dist_result.all()

    # Fill in missing buckets with 0
    dist_map = {row.rating: row.count for row in dist_rows}
    distribution = [
        RatingDistribution(rating=r, count=dist_map.get(r, 0))
        for r in range(1, 6)
    ]

    def _round_or_none(val: float | None) -> float | None:
        return round(float(val), 2) if val is not None else None

    return SurveyStats(
        total_responses=agg.total,
        avg_overall=_round_or_none(agg.avg_overall),
        avg_food=_round_or_none(agg.avg_food),
        avg_service=_round_or_none(agg.avg_service),
        avg_ambiance=_round_or_none(agg.avg_ambiance),
        avg_drinks=_round_or_none(agg.avg_drinks),
        distribution=distribution,
    )
