import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.guest import (
    GuestCreate,
    GuestDetailRead,
    GuestListRead,
    GuestRead,
    GuestUpdate,
)
from app.services import guest as guest_service

router = APIRouter(tags=["guests"])


@router.get(
    "/guests",
    response_model=PaginatedEnvelope[GuestListRead],
)
async def list_guests(
    search: str | None = Query(None, max_length=255, description="Search name or email"),
    tag_id: uuid.UUID | None = Query(None, description="Filter by tag"),
    venue_id: uuid.UUID | None = Query(None, description="Filter by venue (via visits)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    format: str = Query("json", description="Response format: json or csv"),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    if format == "csv":
        # CSV export — up to 10,000 rows
        items, total = await guest_service.list_guests(
            db, org.id, search=search, tag_id=tag_id, venue_id=venue_id,
            page=1, per_page=10_000,
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Email", "Phone", "Visits", "Tags"])
        for g in items:
            name = f"{g.first_name or ''} {g.last_name or ''}".strip()
            tags = ", ".join(g.tag_names) if g.tag_names else ""
            # CSV injection protection
            for val in [name, g.email, g.phone, tags]:
                pass  # handled in row below
            row = []
            for val in [name, g.email or "", g.phone or "", g.total_visits, tags]:
                s = str(val)
                if s and s[0] in ("=", "+", "-", "@", "\t"):
                    s = f"'{s}"
                row.append(s)
            writer.writerow(row)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="guests.csv"'},
        )

    items, total = await guest_service.list_guests(
        db,
        org.id,
        search=search,
        tag_id=tag_id,
        venue_id=venue_id,
        page=page,
        per_page=per_page,
    )
    return paginated(items, page=page, per_page=per_page, total=total)


@router.post(
    "/guests",
    response_model=Envelope[GuestRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_guest(
    body: GuestCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    guest = await guest_service.create_guest(db, org.id, body)
    return ok(guest)


@router.get(
    "/guests/{guest_id}",
    response_model=Envelope[GuestDetailRead],
)
async def get_guest(
    guest_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    detail = await guest_service.get_guest_detail(db, guest_id, org.id)
    return ok(detail)


@router.patch(
    "/guests/{guest_id}",
    response_model=Envelope[GuestRead],
)
async def update_guest(
    guest_id: uuid.UUID,
    body: GuestUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    guest = await guest_service.update_guest(db, guest_id, org.id, body)
    return ok(guest)
