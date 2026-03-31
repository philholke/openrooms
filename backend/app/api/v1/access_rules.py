import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.models.venue import Venue
from app.schemas.access_rule import AccessRuleCreate, AccessRuleRead, AccessRuleUpdate
from app.schemas.envelope import Envelope, ok
from app.services import access_rule as access_rule_service
from app.api.v1.venues import _get_venue_or_404

router = APIRouter(tags=["access-rules"])


# ── Venue-scoped routes ──────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/access-rules",
    response_model=Envelope[list[AccessRuleRead]],
)
async def list_access_rules(
    venue_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    rules = await access_rule_service.list_access_rules(db, venue_id)
    return ok([AccessRuleRead.model_validate(r) for r in rules])


@router.post(
    "/venues/{venue_id}/access-rules",
    response_model=Envelope[AccessRuleRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_access_rule(
    venue_id: uuid.UUID,
    body: AccessRuleCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    rule = await access_rule_service.create_access_rule(db, venue_id, body)
    return ok(AccessRuleRead.model_validate(rule))


# ── Direct rule routes ───────────────────────────────────────────────────

@router.get(
    "/access-rules/{rule_id}",
    response_model=Envelope[AccessRuleRead],
)
async def get_access_rule(
    rule_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.reservation import AccessRule as AccessRuleModel
    from fastapi import HTTPException
    from sqlalchemy import select

    result = await db.execute(
        select(AccessRuleModel).where(AccessRuleModel.id == rule_id)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access rule not found")

    await _get_venue_or_404(db, existing.venue_id, org.id)
    return ok(AccessRuleRead.model_validate(existing))


@router.patch(
    "/access-rules/{rule_id}",
    response_model=Envelope[AccessRuleRead],
)
async def update_access_rule(
    rule_id: uuid.UUID,
    body: AccessRuleUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    # We need to find the rule and verify it belongs to a venue in this org.
    # The service layer checks venue_id, so we need to resolve it first.
    from app.models.reservation import AccessRule as AccessRuleModel
    from sqlalchemy import select

    result = await db.execute(
        select(AccessRuleModel).where(AccessRuleModel.id == rule_id)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access rule not found")

    # Verify the venue belongs to this org
    await _get_venue_or_404(db, existing.venue_id, org.id)

    rule = await access_rule_service.update_access_rule(
        db, rule_id, existing.venue_id, body
    )
    return ok(AccessRuleRead.model_validate(rule))


@router.delete(
    "/access-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_access_rule(
    rule_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.reservation import AccessRule as AccessRuleModel
    from sqlalchemy import select

    result = await db.execute(
        select(AccessRuleModel).where(AccessRuleModel.id == rule_id)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access rule not found")

    await _get_venue_or_404(db, existing.venue_id, org.id)
    await access_rule_service.deactivate_access_rule(db, rule_id, existing.venue_id)
