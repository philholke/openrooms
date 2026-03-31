"""
Survey service — CRUD for post-visit feedback surveys.
"""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.survey import Survey
from app.schemas.survey import SurveyCreate, SurveyRead

logger = logging.getLogger(__name__)


async def create_survey(
    db: AsyncSession,
    data: SurveyCreate,
) -> SurveyRead:
    """Create a survey response."""
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
) -> SurveyRead:
    """Get a single survey by ID."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id)
    )
    survey = result.scalar_one_or_none()
    if survey is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")
    return SurveyRead.model_validate(survey)
