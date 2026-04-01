import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.floor_plan import FloorPlan
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, ok
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
from app.services import floor_plan as floor_plan_service
from app.api.v1.venues import _get_venue_or_404

router = APIRouter(tags=["floor-plans"])


# ─── Helpers ────────────────────────────────────────────────────────────

async def _verify_floor_plan_org(
    db: AsyncSession, floor_plan_id: uuid.UUID, org_id: uuid.UUID,
) -> FloorPlan:
    """Look up a floor plan and verify it belongs to an org-owned venue."""
    result = await db.execute(
        select(FloorPlan).where(FloorPlan.id == floor_plan_id)
    )
    fp = result.scalar_one_or_none()
    if fp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Floor plan not found")
    await _get_venue_or_404(db, fp.venue_id, org_id)
    return fp


# ─── Venue-scoped routes ─────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/floor-plans",
    response_model=Envelope[list[FloorPlanRead]],
)
async def list_floor_plans(
    venue_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    plans = await floor_plan_service.list_floor_plans(db, venue_id)
    return ok(plans)


@router.post(
    "/venues/{venue_id}/floor-plans",
    response_model=Envelope[FloorPlanRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_floor_plan(
    venue_id: uuid.UUID,
    body: FloorPlanCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    plan = await floor_plan_service.create_floor_plan(db, venue_id, body)
    return ok(plan)


@router.get(
    "/floor-plans/{floor_plan_id}",
    response_model=Envelope[FloorPlanRead],
)
async def get_floor_plan(
    floor_plan_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    fp = await _verify_floor_plan_org(db, floor_plan_id, org.id)
    return ok(FloorPlanRead.model_validate(fp))


@router.patch(
    "/floor-plans/{floor_plan_id}",
    response_model=Envelope[FloorPlanRead],
)
async def update_floor_plan(
    floor_plan_id: uuid.UUID,
    body: FloorPlanUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    fp = await _verify_floor_plan_org(db, floor_plan_id, org.id)
    updated = await floor_plan_service.update_floor_plan(
        db, floor_plan_id, fp.venue_id, body,
    )
    return ok(updated)


@router.delete(
    "/floor-plans/{floor_plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_floor_plan(
    floor_plan_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    fp = await _verify_floor_plan_org(db, floor_plan_id, org.id)
    await floor_plan_service.deactivate_floor_plan(db, floor_plan_id, fp.venue_id)


# ─── Table status routes ────────────────────────────────────────────────

@router.get(
    "/venues/{venue_id}/table-statuses",
    response_model=Envelope[list[TableStatusRead]],
)
async def get_table_statuses(
    venue_id: uuid.UUID,
    for_date: date = Query(None, alias="date"),
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    await _get_venue_or_404(db, venue_id, org.id)
    if for_date is None:
        for_date = date.today()
    statuses = await floor_plan_service.get_table_statuses(db, venue_id, for_date)
    return ok(statuses)


# ─── Table routes (nested under floor plan) ──────────────────────────────

@router.get(
    "/floor-plans/{floor_plan_id}/tables",
    response_model=Envelope[list[TableRead]],
)
async def list_tables(
    floor_plan_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("staff")),
    db: AsyncSession = Depends(get_db),
):
    fp = await _verify_floor_plan_org(db, floor_plan_id, org.id)
    tables = await floor_plan_service.list_tables(db, floor_plan_id, fp.venue_id)
    return ok(tables)


@router.post(
    "/floor-plans/{floor_plan_id}/tables",
    response_model=Envelope[TableRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_table(
    floor_plan_id: uuid.UUID,
    body: TableCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    await _verify_floor_plan_org(db, floor_plan_id, org.id)
    table = await floor_plan_service.create_table(db, floor_plan_id, body)
    return ok(table)


@router.patch(
    "/tables/{table_id}",
    response_model=Envelope[TableRead],
)
async def update_table(
    table_id: uuid.UUID,
    body: TableUpdate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.floor_plan import Table

    result = await db.execute(
        select(Table).where(Table.id == table_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")

    await _verify_floor_plan_org(db, table.floor_plan_id, org.id)
    updated = await floor_plan_service.update_table(db, table_id, body)
    return ok(updated)


@router.patch(
    "/tables/{table_id}/hold",
    response_model=Envelope[TableRead],
)
async def hold_table(
    table_id: uuid.UUID,
    body: TableHoldRequest,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.floor_plan import Table

    result = await db.execute(
        select(Table).where(Table.id == table_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")

    await _verify_floor_plan_org(db, table.floor_plan_id, org.id)
    updated = await floor_plan_service.hold_table(db, table_id, body)
    return ok(updated)


@router.delete(
    "/tables/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_table(
    table_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.floor_plan import Table

    result = await db.execute(
        select(Table).where(Table.id == table_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")

    # Verify org ownership via floor_plan → venue chain
    await _verify_floor_plan_org(db, table.floor_plan_id, org.id)
    await floor_plan_service.deactivate_table(db, table_id)
