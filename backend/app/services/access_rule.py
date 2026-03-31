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
    updates = data.model_dump(exclude_unset=True)

    # Cross-field validation against existing DB values for partial updates.
    # The schema validates when both fields are provided; here we catch the
    # case where only one of a pair is updated.
    eff_start = updates.get("start_time", rule.start_time)
    eff_end = updates.get("end_time", rule.end_time)
    if eff_start >= eff_end:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "start_time must be before end_time",
        )

    eff_min = updates.get("min_party_size", rule.min_party_size)
    eff_max = updates.get("max_party_size", rule.max_party_size)
    if eff_min > eff_max:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "min_party_size must be <= max_party_size",
        )

    eff_require_deposit = updates.get("require_deposit", rule.require_deposit)
    eff_deposit_amount = updates.get("deposit_amount_cents", rule.deposit_amount_cents)
    if eff_require_deposit and not eff_deposit_amount:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "deposit_amount_cents is required when require_deposit is true",
        )

    for field, value in updates.items():
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
