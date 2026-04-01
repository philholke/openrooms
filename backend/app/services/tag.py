"""
Tag service — CRUD for org-scoped tags and manual guest tagging.

Tags come in two flavours:
- Manual tags: created and assigned by staff (e.g. "VIP", "Corporate").
- Auto-tags: created by staff but assigned/removed only by the rule engine
  (Phase 4C). The API prevents manual assignment of auto-tags to guests.
"""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import GuestProfile, guest_tags
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate

logger = logging.getLogger(__name__)


async def list_tags(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    is_auto: bool | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[TagRead], int]:
    """List tags in an org, optionally filtered by is_auto."""
    base = select(Tag).where(Tag.org_id == org_id)
    if is_auto is not None:
        base = base.where(Tag.is_auto == is_auto)

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(Tag.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    tags = result.scalars().all()

    return [TagRead.model_validate(t) for t in tags], total


async def create_tag(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: TagCreate,
) -> TagRead:
    """Create a tag. Catches duplicate (org_id, name) → 409."""
    tag = Tag(org_id=org_id, **data.model_dump())
    db.add(tag)
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A tag named '{data.name}' already exists in this organization",
        )
    await db.refresh(tag)

    logger.info("Tag created: id=%s org=%s name=%s auto=%s", tag.id, org_id, data.name, data.is_auto)
    return TagRead.model_validate(tag)


async def update_tag(
    db: AsyncSession,
    tag_id: uuid.UUID,
    org_id: uuid.UUID,
    data: TagUpdate,
) -> TagRead:
    """Partial update of a tag. Cannot change is_auto."""
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.org_id == org_id)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return TagRead.model_validate(tag)

    # Check name uniqueness if name is being changed
    new_name = update_data.get("name")
    if new_name is not None and new_name != tag.name:
        dup_result = await db.execute(
            select(Tag.id).where(
                Tag.org_id == org_id,
                Tag.name == new_name,
                Tag.id != tag_id,
            )
        )
        if dup_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"A tag named '{new_name}' already exists in this organization",
            )

    for field, value in update_data.items():
        setattr(tag, field, value)

    await db.flush()
    await db.refresh(tag)

    logger.info("Tag updated: id=%s org=%s", tag_id, org_id)
    return TagRead.model_validate(tag)


async def delete_tag(
    db: AsyncSession,
    tag_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    """
    Hard-delete a tag. CASCADE on guest_tags FK removes all associations.
    """
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.org_id == org_id)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")

    await db.delete(tag)
    await db.flush()

    logger.info("Tag deleted: id=%s org=%s name=%s", tag_id, org_id, tag.name)


async def add_tag_to_guest(
    db: AsyncSession,
    guest_id: uuid.UUID,
    tag_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    """
    Add a manual tag to a guest. Validates both belong to the same org.
    Idempotent — no error if already tagged.
    Auto-tags cannot be manually assigned.
    """
    # Validate tag exists and belongs to org
    tag_result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.org_id == org_id)
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")

    if tag.is_auto:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Auto-tags cannot be manually assigned — they are managed by the rule engine",
        )

    # Validate guest exists and belongs to org
    guest_result = await db.execute(
        select(GuestProfile.id).where(
            GuestProfile.id == guest_id,
            GuestProfile.org_id == org_id,
        )
    )
    if guest_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found")

    # Insert with conflict ignore for idempotency
    try:
        async with db.begin_nested():
            await db.execute(
                guest_tags.insert().values(guest_id=guest_id, tag_id=tag_id)
            )
    except IntegrityError:
        # Already tagged — idempotent success
        pass

    logger.info("Tag %s added to guest %s", tag_id, guest_id)


async def remove_tag_from_guest(
    db: AsyncSession,
    guest_id: uuid.UUID,
    tag_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    """Remove a tag from a guest. 404 if the association doesn't exist."""
    # Validate tag belongs to org
    tag_result = await db.execute(
        select(Tag.id).where(Tag.id == tag_id, Tag.org_id == org_id)
    )
    if tag_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")

    # Validate guest belongs to org
    guest_result = await db.execute(
        select(GuestProfile.id).where(
            GuestProfile.id == guest_id,
            GuestProfile.org_id == org_id,
        )
    )
    if guest_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found")

    result = await db.execute(
        delete(guest_tags).where(
            guest_tags.c.guest_id == guest_id,
            guest_tags.c.tag_id == tag_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not assigned to this guest")

    logger.info("Tag %s removed from guest %s", tag_id, guest_id)
