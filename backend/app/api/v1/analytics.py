"""
Analytics API endpoints — reservation, guest, and operations reporting.

All endpoints require manager+ role.
"""

import csv
import io
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, require_role
from app.models.organization import Organization
from app.models.user import User
from app.models.venue import Venue
from app.schemas.analytics import (
    GuestAnalytics,
    OperationsAnalytics,
    ReservationAnalytics,
)
from app.services.analytics import (
    get_guest_analytics,
    get_operations_analytics,
    get_reservation_analytics,
)

router = APIRouter(tags=["analytics"])

MAX_DATE_RANGE_DAYS = 365


async def _verify_venue_org(db: AsyncSession, venue_id: uuid.UUID, org_id: uuid.UUID) -> None:
    """Verify the venue belongs to the requesting user's organization."""
    result = await db.execute(
        select(Venue.id).where(
            Venue.id == venue_id,
            Venue.org_id == org_id,
            Venue.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")


def _validate_dates(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_from must be before or equal to date_to",
        )
    if (date_to - date_from).days > MAX_DATE_RANGE_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Date range must not exceed {MAX_DATE_RANGE_DAYS} days",
        )


def _validate_granularity(granularity: str) -> str:
    if granularity not in ("day", "week", "month"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "granularity must be one of: day, week, month",
        )
    return granularity


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    """Build a CSV streaming response from a list of dicts."""
    if not rows:
        output = io.StringIO("No data\n")
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            # CSV injection protection: prefix cells starting with =, +, -, @
            safe_row = {}
            for k, v in row.items():
                s = str(v) if v is not None else ""
                if s and s[0] in ("=", "+", "-", "@", "\t"):
                    s = f"'{s}"
                safe_row[k] = s
            writer.writerow(safe_row)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Reservation Analytics ──────────────────────────────────────────────


@router.get(
    "/venues/{venue_id}/analytics/reservations",
    response_model=ReservationAnalytics,
)
async def reservation_analytics(
    venue_id: uuid.UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    granularity: str = Query("day"),
    format: str = Query("json"),
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    _validate_dates(date_from, date_to)
    granularity = _validate_granularity(granularity)
    await _verify_venue_org(db, venue_id, org.id)

    data = await get_reservation_analytics(db, venue_id, date_from, date_to, granularity)

    if format == "csv":
        rows = [p.model_dump() for p in data.by_period]
        return _csv_response(rows, f"reservations-{date_from}-to-{date_to}.csv")

    return data


# ─── Guest Analytics ────────────────────────────────────────────────────


@router.get("/analytics/guests", response_model=GuestAnalytics)
async def guest_analytics(
    date_from: date = Query(...),
    date_to: date = Query(...),
    granularity: str = Query("month"),
    format: str = Query("json"),
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    _validate_dates(date_from, date_to)
    granularity = _validate_granularity(granularity)

    data = await get_guest_analytics(db, org.id, date_from, date_to, granularity)

    if format == "csv":
        rows = [g.model_dump() for g in data.growth]
        return _csv_response(rows, f"guests-{date_from}-to-{date_to}.csv")

    return data


# ─── Operations Analytics ───────────────────────────────────────────────


@router.get(
    "/venues/{venue_id}/analytics/operations",
    response_model=OperationsAnalytics,
)
async def operations_analytics(
    venue_id: uuid.UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    format: str = Query("json"),
    _user: User = Depends(require_role("manager")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    _validate_dates(date_from, date_to)
    await _verify_venue_org(db, venue_id, org.id)

    data = await get_operations_analytics(db, venue_id, date_from, date_to)

    if format == "csv":
        rows = [s.model_dump() for s in data.utilization_by_section]
        return _csv_response(rows, f"operations-{date_from}-to-{date_to}.csv")

    return data
