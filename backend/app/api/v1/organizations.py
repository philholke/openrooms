from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, ok
from app.schemas.organization import OrgRead, OrgUpdate

router = APIRouter(prefix="/org", tags=["organization"])


@router.get("", response_model=Envelope[OrgRead])
async def get_org(
    org: Organization = Depends(get_current_org),
):
    return ok(OrgRead.model_validate(org))


@router.patch("", response_model=Envelope[OrgRead])
async def update_org(
    body: OrgUpdate,
    org: Organization = Depends(get_current_org),
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if body.slug is not None and body.slug != org.slug:
        existing = await db.execute(
            select(Organization).where(
                Organization.slug == body.slug,
                Organization.id != org.id,
                Organization.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Slug already taken")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.flush()
    await db.refresh(org)
    return ok(OrgRead.model_validate(org))
