"""
Report service — generate pre-shift reports.
"""

import uuid
from collections import defaultdict
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.floor_plan import Table
from app.models.guest import GuestProfile, GuestVisit
from app.models.reservation import Reservation
from app.models.server_assignment import ServerAssignment
from app.models.venue import Venue
from app.schemas.report import PreShiftReport, PreShiftReportEntry, SectionSummary

# Only include reservations likely to arrive
_REPORT_STATUSES = ["pending", "confirmed", "arrived", "partially_arrived", "seated"]


async def generate_pre_shift_report(
    db: AsyncSession,
    venue_id: uuid.UUID,
    for_date: date,
) -> PreShiftReport:
    # 1. Fetch venue name
    venue_result = await db.execute(select(Venue).where(Venue.id == venue_id))
    venue = venue_result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")

    # 2. Fetch reservations with guests and tables
    res_result = await db.execute(
        select(Reservation)
        .options(
            selectinload(Reservation.guest).selectinload(GuestProfile.tags),
            selectinload(Reservation.table),
        )
        .where(
            Reservation.venue_id == venue_id,
            Reservation.date == for_date,
            Reservation.status.in_(_REPORT_STATUSES),
        )
        .order_by(Reservation.time, Reservation.id)
    )
    reservations = res_result.scalars().all()

    # 3. Count visits per guest for "visit_count"
    guest_ids = list({r.guest_id for r in reservations if r.guest_id})
    visit_counts: dict[uuid.UUID, int] = {}
    if guest_ids:
        vc_result = await db.execute(
            select(
                GuestVisit.guest_id,
                func.count(GuestVisit.id).label("cnt"),
            )
            .where(GuestVisit.guest_id.in_(guest_ids))
            .group_by(GuestVisit.guest_id)
        )
        for row in vc_result:
            visit_counts[row.guest_id] = int(row.cnt)

    # 4. Fetch server assignments for the date (eagerly load user for name)
    sa_result = await db.execute(
        select(ServerAssignment)
        .options(selectinload(ServerAssignment.user))
        .where(
            ServerAssignment.venue_id == venue_id,
            ServerAssignment.date == for_date,
            ServerAssignment.is_active.is_(True),
        )
    )
    server_by_section: dict[str, str] = {}
    for sa in sa_result.scalars().all():
        if sa.user:
            server_by_section[sa.section] = sa.user.full_name
        else:
            server_by_section[sa.section] = str(sa.user_id)

    # 5. Build table → section map
    table_sections: dict[uuid.UUID, str] = {}
    if reservations:
        table_ids = [r.table_id for r in reservations if r.table_id]
        if table_ids:
            t_result = await db.execute(
                select(Table).where(Table.id.in_(table_ids))
            )
            for t in t_result.scalars().all():
                table_sections[t.id] = t.section or "Unassigned"

    # 6. Build entries
    entries: list[PreShiftReportEntry] = []
    section_covers: dict[str, int] = defaultdict(int)
    section_tables: dict[str, set[str]] = defaultdict(set)

    for res in reservations:
        guest = res.guest
        guest_name = ""
        dietary = None
        tags: list[str] = []

        if guest:
            guest_name = f"{guest.first_name} {guest.last_name}".strip()
            dietary = guest.dietary_restrictions
            tags = [t.name for t in (guest.tags or [])]

        table_label = res.table.label if res.table else None
        section = table_sections.get(res.table_id) if res.table_id else None

        if section:
            section_covers[section] += res.party_size
            if table_label:
                section_tables[section].add(table_label)

        time_str = res.time.strftime("%H:%M") if hasattr(res.time, "strftime") else str(res.time)[:5]

        entries.append(PreShiftReportEntry(
            time=time_str,
            guest_name=guest_name,
            party_size=res.party_size,
            table_label=table_label,
            section=section,
            status=res.status,
            special_requests=res.special_requests,
            notes=res.notes,
            dietary_restrictions=dietary,
            tags=tags,
            visit_count=visit_counts.get(res.guest_id, 0),
        ))

    # 7. Build section summaries
    all_sections = set(section_covers.keys()) | set(server_by_section.keys())
    sections = [
        SectionSummary(
            section=s,
            server_name=server_by_section.get(s),
            covers=section_covers.get(s, 0),
            table_count=len(section_tables.get(s, set())),
        )
        for s in sorted(all_sections)
    ]

    return PreShiftReport(
        date=for_date,
        venue_name=venue.name,
        total_covers=sum(r.party_size for r in reservations),
        total_reservations=len(reservations),
        sections=sections,
        entries=entries,
    )
