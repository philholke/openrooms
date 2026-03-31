"""
FloorPlan & Table service — CRUD for venue floor plans and tables.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.floor_plan import FloorPlan, Table
from app.schemas.floor_plan import (
    FloorPlanCreate,
    FloorPlanRead,
    TableCreate,
    TableRead,
)


# ─── Floor Plans ────────────────────────────────────────────────────────

async def list_floor_plans(
    db: AsyncSession,
    venue_id: uuid.UUID,
) -> list[FloorPlanRead]:
    result = await db.execute(
        select(FloorPlan)
        .where(FloorPlan.venue_id == venue_id, FloorPlan.is_active.is_(True))
        .order_by(FloorPlan.name)
    )
    return [FloorPlanRead.model_validate(fp) for fp in result.scalars().all()]


async def create_floor_plan(
    db: AsyncSession,
    venue_id: uuid.UUID,
    data: FloorPlanCreate,
) -> FloorPlanRead:
    fp = FloorPlan(venue_id=venue_id, **data.model_dump())
    db.add(fp)
    await db.flush()
    await db.refresh(fp)
    return FloorPlanRead.model_validate(fp)


async def get_floor_plan(
    db: AsyncSession,
    floor_plan_id: uuid.UUID,
    venue_id: uuid.UUID,
) -> FloorPlan:
    result = await db.execute(
        select(FloorPlan).where(
            FloorPlan.id == floor_plan_id,
            FloorPlan.venue_id == venue_id,
            FloorPlan.is_active.is_(True),
        )
    )
    fp = result.scalar_one_or_none()
    if fp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Floor plan not found")
    return fp


async def deactivate_floor_plan(
    db: AsyncSession,
    floor_plan_id: uuid.UUID,
    venue_id: uuid.UUID,
) -> None:
    fp = await get_floor_plan(db, floor_plan_id, venue_id)
    fp.is_active = False
    await db.flush()


# ─── Tables ─────────────────────────────────────────────────────────────

async def list_tables(
    db: AsyncSession,
    floor_plan_id: uuid.UUID,
) -> list[TableRead]:
    result = await db.execute(
        select(Table)
        .where(Table.floor_plan_id == floor_plan_id, Table.is_active.is_(True))
        .order_by(Table.label)
    )
    return [TableRead.model_validate(t) for t in result.scalars().all()]


async def create_table(
    db: AsyncSession,
    floor_plan_id: uuid.UUID,
    data: TableCreate,
) -> TableRead:
    table = Table(floor_plan_id=floor_plan_id, **data.model_dump())
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return TableRead.model_validate(table)


async def get_table(
    db: AsyncSession,
    table_id: uuid.UUID,
) -> Table:
    result = await db.execute(
        select(Table).where(Table.id == table_id, Table.is_active.is_(True))
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")
    return table


async def deactivate_table(
    db: AsyncSession,
    table_id: uuid.UUID,
) -> None:
    table = await get_table(db, table_id)
    table.is_active = False
    await db.flush()
