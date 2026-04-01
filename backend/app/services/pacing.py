"""
Pacing service — compute covers-per-slot for a venue on a given date.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.floor_plan import FloorPlan, Table
from app.models.reservation import Reservation
from app.schemas.pacing import PacingResponse, PacingSlot

# Statuses that count as active bookings for pacing purposes
_ACTIVE_STATUSES = ["pending", "confirmed", "arrived", "partially_arrived", "seated"]


async def get_pacing(
    db: AsyncSession,
    venue_id: uuid.UUID,
    for_date: date,
) -> PacingResponse:
    # 1. Sum booked covers grouped by time slot
    covers_result = await db.execute(
        select(
            Reservation.time,
            func.sum(Reservation.party_size).label("covers"),
        )
        .where(
            Reservation.venue_id == venue_id,
            Reservation.date == for_date,
            Reservation.status.in_(_ACTIVE_STATUSES),
        )
        .group_by(Reservation.time)
        .order_by(Reservation.time)
    )
    covers_by_time: dict[str, int] = {}
    for row in covers_result:
        time_str = row.time.strftime("%H:%M") if hasattr(row.time, "strftime") else str(row.time)[:5]
        covers_by_time[time_str] = int(row.covers)

    # 2. Calculate total venue capacity from active tables
    cap_result = await db.execute(
        select(func.coalesce(func.sum(Table.max_capacity), 0))
        .join(FloorPlan, Table.floor_plan_id == FloorPlan.id)
        .where(
            FloorPlan.venue_id == venue_id,
            FloorPlan.is_active.is_(True),
            Table.is_active.is_(True),
        )
    )
    total_capacity = int(cap_result.scalar_one())

    # 3. Build slot list
    slots = [
        PacingSlot(
            time=time_str,
            booked_covers=covers,
            capacity=total_capacity,
        )
        for time_str, covers in sorted(covers_by_time.items())
    ]

    return PacingResponse(
        venue_id=venue_id,
        date=for_date,
        total_capacity=total_capacity,
        slots=slots,
    )
