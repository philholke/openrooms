import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.survey import Survey
from app.models.user import User
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.survey import (
    SurveyCreate,
    SurveyPublicInfo,
    SurveyPublicSubmit,
    SurveyRead,
    SurveyStats,
)
from app.services import survey as survey_service
from app.api.v1.venues import _get_venue_or_404

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["surveys"])


# ─── Venue-scoped routes ─────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/surveys",
    response_model=PaginatedEnvelope[SurveyRead],
)
async def list_surveys(
    venue_id: uuid.UUID,
    guest_id: uuid.UUID = Query(None, description="Filter by guest"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    items, total = await survey_service.list_surveys(
        db, venue_id, guest_id=guest_id, page=page, per_page=per_page,
    )
    return paginated(items, page=page, per_page=per_page, total=total)


@router.post(
    "/venues/{venue_id}/surveys",
    response_model=Envelope[SurveyRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_survey(
    venue_id: uuid.UUID,
    body: SurveyCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    # Ensure the venue_id in the body matches the path
    if body.venue_id != venue_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "venue_id in body must match the path",
        )
    survey = await survey_service.create_survey(db, body, org.id)
    return ok(survey)


# ─── Direct survey routes ────────────────────────────────────────────────

@router.get(
    "/surveys/{survey_id}",
    response_model=Envelope[SurveyRead],
)
async def get_survey(
    survey_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    survey = await survey_service.get_survey(db, survey_id, org_id=org.id)
    return ok(survey)


# ─── Survey stats ────────────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/surveys/stats",
    response_model=Envelope[SurveyStats],
)
async def get_survey_stats(
    venue_id: uuid.UUID,
    date_from: datetime | None = Query(None, description="Start date (ISO 8601)"),
    date_to: datetime | None = Query(None, description="End date (ISO 8601)"),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    stats = await survey_service.get_survey_stats(
        db, venue_id, date_from=date_from, date_to=date_to,
    )
    return ok(stats)


# ─── Public survey endpoints (no auth) ───────────────────────────────────

@router.get(
    "/public/surveys/{token}",
    response_model=Envelope[SurveyPublicInfo],
)
@limiter.limit("30/minute")
async def get_public_survey(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    info = await survey_service.get_dispatch_info(db, token)
    return ok(info)


@router.post(
    "/public/surveys/{token}",
    response_model=Envelope[SurveyRead],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def submit_public_survey(
    request: Request,
    token: str,
    body: SurveyPublicSubmit,
    db: AsyncSession = Depends(get_db),
):
    survey = await survey_service.submit_public_survey(db, token, body)
    return ok(survey)
