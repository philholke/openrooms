import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.waitlist import WaitlistEntryCreate, WaitlistEntryRead, WaitlistEntryUpdate, WaitlistSeatRequest
from app.services import waitlist as waitlist_service
from app.api.v1.venues import _get_venue_or_404

router = APIRouter(tags=["waitlist"])


# ─── Venue-scoped routes ─────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/waitlist",
    response_model=PaginatedEnvelope[WaitlistEntryRead],
)
async def list_waitlist(
    venue_id: uuid.UUID,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    items, total = await waitlist_service.list_waitlist(
        db, venue_id, active_only=active_only, page=page, per_page=per_page,
    )
    return paginated(items, page=page, per_page=per_page, total=total)


@router.post(
    "/venues/{venue_id}/waitlist",
    response_model=Envelope[WaitlistEntryRead],
    status_code=status.HTTP_201_CREATED,
)
async def add_to_waitlist(
    venue_id: uuid.UUID,
    body: WaitlistEntryCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    entry = await waitlist_service.add_to_waitlist(db, venue_id, org.id, body)
    return ok(entry)


# ─── Direct entry routes ─────────────────────────────────────────────────

@router.patch(
    "/waitlist/{entry_id}",
    response_model=Envelope[WaitlistEntryRead],
)
async def update_waitlist_entry(
    entry_id: uuid.UUID,
    body: WaitlistEntryUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.reservation import WaitlistEntry

    result = await db.execute(
        select(WaitlistEntry.venue_id).where(WaitlistEntry.id == entry_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Waitlist entry not found")
    await _get_venue_or_404(db, row.venue_id, org.id)

    entry = await waitlist_service.update_waitlist_entry(
        db, entry_id, row.venue_id, body
    )
    return ok(entry)


@router.post(
    "/waitlist/{entry_id}/seat",
    response_model=Envelope[WaitlistEntryRead],
)
async def seat_from_waitlist(
    entry_id: uuid.UUID,
    body: WaitlistSeatRequest | None = None,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    """Seat a waitlist guest, optionally assigning a table and creating a walk-in reservation."""
    from app.models.reservation import WaitlistEntry

    result = await db.execute(
        select(WaitlistEntry.venue_id).where(WaitlistEntry.id == entry_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Waitlist entry not found")
    await _get_venue_or_404(db, row.venue_id, org.id)

    table_id = body.table_id if body else None
    entry_read, _reservation_data = await waitlist_service.seat_from_waitlist(
        db, entry_id, row.venue_id, table_id=table_id
    )
    return ok(entry_read)


@router.delete(
    "/waitlist/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_waitlist_entry(
    entry_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel/remove a waitlist entry (soft delete via status change)."""
    from app.models.reservation import WaitlistEntry

    result = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Waitlist entry not found")
    await _get_venue_or_404(db, entry.venue_id, org.id)

    if entry.status in ("waiting", "notified"):
        entry.status = "cancelled"
        await db.flush()
