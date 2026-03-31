import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservation import AccessRule
from app.schemas.access_rule import AccessRuleCreate, AccessRuleUpdate


async def create_access_rule(
    db: AsyncSession,
    venue_id: uuid.UUID,
    data: AccessRuleCreate,
) -> AccessRule:
    rule = AccessRule(venue_id=venue_id, **data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def list_access_rules(
    db: AsyncSession,
    venue_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[AccessRule]:
    stmt = select(AccessRule).where(AccessRule.venue_id == venue_id)
    if active_only:
        stmt = stmt.where(AccessRule.is_active.is_(True))
    stmt = stmt.order_by(AccessRule.start_time)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_access_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    venue_id: uuid.UUID,
) -> AccessRule:
    result = await db.execute(
        select(AccessRule).where(
            AccessRule.id == rule_id,
            AccessRule.venue_id == venue_id,
            AccessRule.is_active.is_(True),
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access rule not found")
    return rule


async def update_access_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    venue_id: uuid.UUID,
    data: AccessRuleUpdate,
) -> AccessRule:
    rule = await get_access_rule(db, rule_id, venue_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    return rule


async def deactivate_access_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    venue_id: uuid.UUID,
) -> AccessRule:
    rule = await get_access_rule(db, rule_id, venue_id)
    rule.is_active = False
    await db.flush()
    await db.refresh(rule)
    return rule
