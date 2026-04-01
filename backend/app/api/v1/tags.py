import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.auto_tag_rule import AutoTagRule
from app.models.organization import Organization
from app.models.tag import Tag
from app.models.user import User
from app.schemas.auto_tag_rule import AutoTagRuleCreate, AutoTagRuleRead, BulkEvaluateResult
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services import auto_tag as auto_tag_service
from app.services import tag as tag_service

router = APIRouter(tags=["tags"])


# ─── Tag CRUD ─────────────────────────────────────────────────────────────


@router.get(
    "/tags",
    response_model=PaginatedEnvelope[TagRead],
)
async def list_tags(
    is_auto: bool | None = Query(None, description="Filter by auto-tag status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await tag_service.list_tags(
        db, org.id, is_auto=is_auto, page=page, per_page=per_page,
    )
    return paginated(items, page=page, per_page=per_page, total=total)


@router.post(
    "/tags",
    response_model=Envelope[TagRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    body: TagCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    tag = await tag_service.create_tag(db, org.id, body)
    return ok(tag)


@router.patch(
    "/tags/{tag_id}",
    response_model=Envelope[TagRead],
)
async def update_tag(
    tag_id: uuid.UUID,
    body: TagUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    tag = await tag_service.update_tag(db, tag_id, org.id, body)
    return ok(tag)


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tag(
    tag_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await tag_service.delete_tag(db, tag_id, org.id)


# ─── Guest tagging ───────────────────────────────────────────────────────


class AddTagBody(BaseModel):
    tag_id: uuid.UUID


@router.post(
    "/guests/{guest_id}/tags",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_tag_to_guest(
    guest_id: uuid.UUID,
    body: AddTagBody,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await tag_service.add_tag_to_guest(db, guest_id, body.tag_id, org.id)


@router.delete(
    "/guests/{guest_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_tag_from_guest(
    guest_id: uuid.UUID,
    tag_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await tag_service.remove_tag_from_guest(db, guest_id, tag_id, org.id)


# ─── Auto-tag rules ──────────────────────────────────────────────────────


async def _get_auto_tag_or_404(
    db: AsyncSession, tag_id: uuid.UUID, org_id: uuid.UUID,
) -> Tag:
    """Validate that the tag exists, belongs to the org, and is an auto-tag."""
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.org_id == org_id)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")
    if not tag.is_auto:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Rules can only be attached to auto-tags (is_auto=true)",
        )
    return tag


@router.get(
    "/tags/{tag_id}/rule",
    response_model=Envelope[AutoTagRuleRead],
)
async def get_auto_tag_rule(
    tag_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await _get_auto_tag_or_404(db, tag_id, org.id)

    result = await db.execute(
        select(AutoTagRule).where(
            AutoTagRule.tag_id == tag_id,
            AutoTagRule.org_id == org.id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No rule defined for this tag")

    return ok(AutoTagRuleRead.model_validate(rule))


@router.put(
    "/tags/{tag_id}/rule",
    response_model=Envelope[AutoTagRuleRead],
)
async def upsert_auto_tag_rule(
    tag_id: uuid.UUID,
    body: AutoTagRuleCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await _get_auto_tag_or_404(db, tag_id, org.id)

    # Upsert: find existing rule or create new
    result = await db.execute(
        select(AutoTagRule).where(
            AutoTagRule.tag_id == tag_id,
            AutoTagRule.org_id == org.id,
        )
    )
    rule = result.scalar_one_or_none()

    if rule is not None:
        rule.conditions = body.conditions.model_dump(exclude_none=True)
        rule.is_active = True
    else:
        rule = AutoTagRule(
            tag_id=tag_id,
            org_id=org.id,
            conditions=body.conditions.model_dump(exclude_none=True),
        )
        db.add(rule)

    await db.flush()
    await db.refresh(rule)

    return ok(AutoTagRuleRead.model_validate(rule))


@router.delete(
    "/tags/{tag_id}/rule",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_auto_tag_rule(
    tag_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await _get_auto_tag_or_404(db, tag_id, org.id)

    result = await db.execute(
        select(AutoTagRule).where(
            AutoTagRule.tag_id == tag_id,
            AutoTagRule.org_id == org.id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No rule defined for this tag")

    await db.delete(rule)
    await db.flush()


@router.post(
    "/tags/evaluate",
    response_model=Envelope[BulkEvaluateResult],
)
async def bulk_evaluate_auto_tags(
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await auto_tag_service.evaluate_all_rules(db, org.id)
    return ok(result)
