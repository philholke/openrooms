import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.models.venue import Venue
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.venue import VenueCreate, VenueRead, VenueUpdate

router = APIRouter(prefix="/venues", tags=["venues"])


async def _get_venue_or_404(
    db: AsyncSession, venue_id: uuid.UUID, org_id: uuid.UUID
) -> Venue:
    result = await db.execute(
        select(Venue).where(
            Venue.id == venue_id,
            Venue.org_id == org_id,
            Venue.is_active.is_(True),
        )
    )
    venue = result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")
    return venue


@router.get("", response_model=PaginatedEnvelope[VenueRead])
async def list_venues(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    base = select(Venue).where(Venue.org_id == org.id, Venue.is_active.is_(True))

    total_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_result.scalar_one()

    result = await db.execute(
        base.order_by(Venue.name).offset((page - 1) * per_page).limit(per_page)
    )
    venues = result.scalars().all()

    return paginated(
        [VenueRead.model_validate(v) for v in venues],
        page=page,
        per_page=per_page,
        total=total,
    )


@router.post(
    "",
    response_model=Envelope[VenueRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_venue(
    body: VenueCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Venue).where(
            Venue.org_id == org.id,
            Venue.slug == body.slug,
            Venue.is_active.is_(True),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Venue slug already exists in this org")

    try:
        venue = Venue(org_id=org.id, **body.model_dump())
        db.add(venue)
        await db.flush()
        await db.refresh(venue)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Venue slug already exists in this org")
    return ok(VenueRead.model_validate(venue))


@router.get("/{venue_id}", response_model=Envelope[VenueRead])
async def get_venue(
    venue_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    venue = await _get_venue_or_404(db, venue_id, org.id)
    return ok(VenueRead.model_validate(venue))


@router.patch("/{venue_id}", response_model=Envelope[VenueRead])
async def update_venue(
    venue_id: uuid.UUID,
    body: VenueUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    venue = await _get_venue_or_404(db, venue_id, org.id)

    if body.slug is not None and body.slug != venue.slug:
        existing = await db.execute(
            select(Venue).where(
                Venue.org_id == org.id,
                Venue.slug == body.slug,
                Venue.id != venue.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Venue slug already exists in this org")

    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(venue, field, value)
        await db.flush()
        await db.refresh(venue)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Venue slug already exists in this org")
    return ok(VenueRead.model_validate(venue))


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venue(
    venue_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    venue = await _get_venue_or_404(db, venue_id, org.id)
    venue.is_active = False
    await db.flush()
