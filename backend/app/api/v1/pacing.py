import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, ok
from app.schemas.pacing import PacingResponse
from app.services import pacing as pacing_service
from app.api.v1.venues import _get_venue_or_404

router = APIRouter(tags=["pacing"])


@router.get(
    "/venues/{venue_id}/pacing",
    response_model=Envelope[PacingResponse],
)
async def get_pacing(
    venue_id: uuid.UUID,
    for_date: date = Query(None, alias="date"),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    if for_date is None:
        for_date = date.today()
    result = await pacing_service.get_pacing(db, venue_id, for_date)
    return ok(result)
