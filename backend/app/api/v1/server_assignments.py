import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, ok
from app.schemas.server_assignment import ServerAssignmentCreate, ServerAssignmentRead
from app.services import server_assignment as sa_service
from app.api.v1.venues import _get_venue_or_404

router = APIRouter(tags=["server-assignments"])


@router.get(
    "/venues/{venue_id}/server-assignments",
    response_model=Envelope[list[ServerAssignmentRead]],
)
async def list_server_assignments(
    venue_id: uuid.UUID,
    for_date: date = Query(None, alias="date"),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    if for_date is None:
        for_date = date.today()
    assignments = await sa_service.list_assignments(db, venue_id, for_date)
    return ok(assignments)


@router.post(
    "/venues/{venue_id}/server-assignments",
    response_model=Envelope[ServerAssignmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_server_assignment(
    venue_id: uuid.UUID,
    body: ServerAssignmentCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    assignment = await sa_service.upsert_assignment(db, venue_id, body, org.id)
    return ok(assignment)


@router.delete(
    "/server-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_server_assignment(
    assignment_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await sa_service.delete_assignment(db, assignment_id, org.id)
