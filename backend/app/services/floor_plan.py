"""
FloorPlan & Table service — CRUD for venue floor plans and tables.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.floor_plan import FloorPlan, Table
from app.models.reservation import Reservation
from app.schemas.floor_plan import (
    FloorPlanCreate,
    FloorPlanRead,
    FloorPlanUpdate,
    TableCreate,
    TableHoldRequest,
    TableRead,
    TableStatusRead,
    TableUpdate,
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


async def update_floor_plan(
    db: AsyncSession,
    floor_plan_id: uuid.UUID,
    venue_id: uuid.UUID,
    data: FloorPlanUpdate,
) -> FloorPlanRead:
    fp = await get_floor_plan(db, floor_plan_id, venue_id)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(fp, key, value)
    await db.flush()
    await db.refresh(fp)
    return FloorPlanRead.model_validate(fp)


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


async def update_table(
    db: AsyncSession,
    table_id: uuid.UUID,
    data: TableUpdate,
) -> TableRead:
    table = await get_table(db, table_id)
    updates = data.model_dump(exclude_unset=True)

    # Cross-validate capacity against existing values when only one is provided
    eff_min = updates.get("min_capacity", table.min_capacity)
    eff_max = updates.get("max_capacity", table.max_capacity)
    if eff_min > eff_max:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "min_capacity must be <= max_capacity",
        )

    for key, value in updates.items():
        setattr(table, key, value)
    await db.flush()
    await db.refresh(table)
    return TableRead.model_validate(table)


async def deactivate_table(
    db: AsyncSession,
    table_id: uuid.UUID,
) -> None:
    table = await get_table(db, table_id)
    table.is_active = False
    await db.flush()


# ─── Table Status Engine ───────────────────────────────────────────────

# Reservation statuses that occupy a table or indicate an upcoming booking
_SEATED_STATUSES = ["seated"]
_UPCOMING_STATUSES = ["confirmed", "arrived", "partially_arrived"]

LOOKAHEAD_MINUTES = 30


async def get_table_statuses(
    db: AsyncSession,
    venue_id: uuid.UUID,
    for_date: date,
) -> list[TableStatusRead]:
    """Compute live status for all active tables in a venue."""
    # 1. Load all active tables for this venue (via floor plan join)
    table_result = await db.execute(
        select(Table)
        .join(FloorPlan, Table.floor_plan_id == FloorPlan.id)
        .where(
            FloorPlan.venue_id == venue_id,
            FloorPlan.is_active.is_(True),
            Table.is_active.is_(True),
        )
        .order_by(FloorPlan.name, Table.label)
    )
    tables = table_result.scalars().all()

    if not tables:
        return []

    table_ids = [t.id for t in tables]

    # 2. Load today's reservations that are assigned to any of these tables
    res_result = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.guest))
        .where(
            Reservation.table_id.in_(table_ids),
            Reservation.date == for_date,
            Reservation.status.in_(_SEATED_STATUSES + _UPCOMING_STATUSES),
        )
    )
    reservations = res_result.scalars().all()

    # Index reservations by table_id
    seated_by_table: dict[uuid.UUID, Reservation] = {}
    upcoming_by_table: dict[uuid.UUID, Reservation] = {}

    now = datetime.now(timezone.utc)
    lookahead = now + timedelta(minutes=LOOKAHEAD_MINUTES)

    for res in reservations:
        if res.table_id is None:
            continue
        if res.status in _SEATED_STATUSES:
            seated_by_table[res.table_id] = res
        elif res.status in _UPCOMING_STATUSES:
            # Check if reservation is within lookahead window
            res_dt = datetime.combine(res.date, res.time, tzinfo=timezone.utc)
            if res_dt <= lookahead:
                # Keep the earliest upcoming reservation per table
                existing = upcoming_by_table.get(res.table_id)
                if existing is None:
                    upcoming_by_table[res.table_id] = res
                else:
                    existing_dt = datetime.combine(
                        existing.date, existing.time, tzinfo=timezone.utc,
                    )
                    if res_dt < existing_dt:
                        upcoming_by_table[res.table_id] = res

    # 3. Compute status for each table
    result: list[TableStatusRead] = []
    for table in tables:
        status_str = "available"
        current_res: Reservation | None = None

        if table.held_until is not None and table.held_until > now:
            status_str = "held"
        elif table.id in seated_by_table:
            status_str = "occupied"
            current_res = seated_by_table[table.id]
        elif table.id in upcoming_by_table:
            status_str = "reserved"
            current_res = upcoming_by_table[table.id]

        guest_name = None
        if current_res and current_res.guest:
            guest_name = (
                f"{current_res.guest.first_name} {current_res.guest.last_name}"
            ).strip()

        result.append(TableStatusRead(
            id=table.id,
            floor_plan_id=table.floor_plan_id,
            label=table.label,
            min_capacity=table.min_capacity,
            max_capacity=table.max_capacity,
            section=table.section,
            x_position=table.x_position,
            y_position=table.y_position,
            shape=table.shape,
            held_until=table.held_until,
            is_active=table.is_active,
            status=status_str,
            current_reservation_id=current_res.id if current_res else None,
            current_guest_name=guest_name,
            current_party_size=current_res.party_size if current_res else None,
            next_reservation_time=(
                current_res.time.isoformat()
                if current_res and status_str == "reserved"
                else None
            ),
        ))

    return result


async def hold_table(
    db: AsyncSession,
    table_id: uuid.UUID,
    data: TableHoldRequest,
) -> TableRead:
    """Set or clear a hold on a table."""
    table = await get_table(db, table_id)
    table.held_until = data.held_until
    await db.flush()
    await db.refresh(table)
    return TableRead.model_validate(table)
