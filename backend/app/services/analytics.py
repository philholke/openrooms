"""
Analytics service — aggregation queries for reservation, guest, and
operations reporting.

All queries are read-only and operate on the transactional database.
For large datasets (>100K reservations), consider materialized views
or a separate OLAP store.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import case, cast, func, select, Float, Integer, String, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import GuestProfile, GuestVisit, guest_tags
from app.models.reservation import Reservation, WaitlistEntry
from app.models.tag import Tag
from app.schemas.analytics import (
    DayOfWeekStats,
    GuestAnalytics,
    GuestGrowth,
    GuestSummary,
    HourStats,
    OperationsAnalytics,
    OperationsSummary,
    PeriodReservations,
    ReservationAnalytics,
    ReservationSummary,
    SectionUtilization,
    SourceBreakdown,
    StatusBreakdown,
    TagDistribution,
    TopGuest,
    TurnTimeByPartySize,
    WaitlistStats,
)

logger = logging.getLogger(__name__)

DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Postgres extract('dow') returns 0=Sunday. We convert to 0=Monday.
_PG_DOW_TO_ISO = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}


def _trunc_expr(granularity: str, column):
    """Return a date_trunc expression for the given granularity."""
    g = {"day": "day", "week": "week", "month": "month"}.get(granularity, "day")
    return func.date_trunc(g, column)


# ─── Reservation Analytics ──────────────────────────────────────────────


async def get_reservation_analytics(
    db: AsyncSession,
    venue_id: uuid.UUID,
    date_from: date,
    date_to: date,
    granularity: str = "day",
) -> ReservationAnalytics:
    base = select(Reservation).where(
        Reservation.venue_id == venue_id,
        Reservation.date >= date_from,
        Reservation.date <= date_to,
    )

    # ── Summary ──
    summary_result = await db.execute(
        select(
            func.count(Reservation.id).label("total"),
            func.coalesce(func.sum(Reservation.party_size), 0).label("covers"),
            func.coalesce(func.avg(cast(Reservation.party_size, Float)), 0).label("avg_party"),
            func.count(case((Reservation.status == "cancelled", 1))).label("cancelled"),
            func.count(case((Reservation.status == "no_show", 1))).label("no_show"),
            func.count(case((Reservation.status == "completed", 1))).label("completed"),
            func.coalesce(
                func.avg(
                    extract("epoch", cast(Reservation.date, String) + " " + cast(Reservation.time, String))
                    - extract("epoch", Reservation.created_at)
                ) / 86400,
                0,
            ).label("avg_lead_days"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        )
    )
    row = summary_result.one()
    total = row.total or 1  # avoid division by zero

    summary = ReservationSummary(
        total_reservations=row.total,
        total_covers=row.covers,
        avg_party_size=round(float(row.avg_party), 1),
        cancellation_rate=round(row.cancelled / total, 3),
        no_show_rate=round(row.no_show / total, 3),
        completion_rate=round(row.completed / total, 3),
        avg_lead_time_days=round(float(row.avg_lead_days), 1) if row.avg_lead_days else 0,
    )

    # ── By period ──
    trunc = _trunc_expr(granularity, Reservation.date)
    period_result = await db.execute(
        select(
            cast(trunc, String).label("period"),
            func.count(Reservation.id).label("reservations"),
            func.coalesce(func.sum(Reservation.party_size), 0).label("covers"),
            func.count(case((Reservation.status == "cancelled", 1))).label("cancellations"),
            func.count(case((Reservation.status == "no_show", 1))).label("no_shows"),
            func.count(case((Reservation.status == "completed", 1))).label("completions"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        ).group_by(trunc).order_by(trunc)
    )
    by_period = [
        PeriodReservations(
            period=r.period[:10],  # trim timestamp to date
            reservations=r.reservations,
            covers=r.covers,
            cancellations=r.cancellations,
            no_shows=r.no_shows,
            completions=r.completions,
        )
        for r in period_result
    ]

    # ── By status ──
    status_result = await db.execute(
        select(
            Reservation.status,
            func.count(Reservation.id).label("cnt"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        ).group_by(Reservation.status)
    )
    status_map = {r.status: r.cnt for r in status_result}
    by_status = StatusBreakdown(**{k: status_map.get(k, 0) for k in StatusBreakdown.model_fields})

    # ── By source ──
    source_result = await db.execute(
        select(
            func.coalesce(Reservation.source, "unknown").label("source"),
            func.count(Reservation.id).label("cnt"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        ).group_by("source").order_by(func.count(Reservation.id).desc())
    )
    by_source = [SourceBreakdown(source=r.source, count=r.cnt) for r in source_result]

    # ── By day of week ──
    dow = extract("dow", Reservation.date)
    dow_result = await db.execute(
        select(
            cast(dow, Integer).label("pg_dow"),
            func.count(Reservation.id).label("reservations"),
            func.coalesce(func.sum(Reservation.party_size), 0).label("covers"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        ).group_by(dow).order_by(dow)
    )
    by_day_of_week = [
        DayOfWeekStats(
            day=_PG_DOW_TO_ISO.get(r.pg_dow, r.pg_dow),
            label=DAY_LABELS[_PG_DOW_TO_ISO.get(r.pg_dow, r.pg_dow)],
            reservations=r.reservations,
            covers=r.covers,
        )
        for r in dow_result
    ]

    # ── Peak hours ──
    hour = extract("hour", Reservation.time)
    hour_result = await db.execute(
        select(
            cast(hour, Integer).label("hour"),
            func.count(Reservation.id).label("reservations"),
            func.coalesce(func.sum(Reservation.party_size), 0).label("covers"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        ).group_by(hour).order_by(hour)
    )
    peak_hours = [
        HourStats(hour=r.hour, reservations=r.reservations, covers=r.covers)
        for r in hour_result
    ]

    return ReservationAnalytics(
        summary=summary,
        by_period=by_period,
        by_status=by_status,
        by_source=by_source,
        by_day_of_week=by_day_of_week,
        peak_hours=peak_hours,
    )


# ─── Guest Analytics ────────────────────────────────────────────────────


async def get_guest_analytics(
    db: AsyncSession,
    org_id: uuid.UUID,
    date_from: date,
    date_to: date,
    granularity: str = "month",
) -> GuestAnalytics:
    # ── Summary ──
    total_result = await db.execute(
        select(func.count(GuestProfile.id)).where(
            GuestProfile.org_id == org_id,
        )
    )
    total_guests = total_result.scalar_one()

    new_result = await db.execute(
        select(func.count(GuestProfile.id)).where(
            GuestProfile.org_id == org_id,
            func.date(GuestProfile.created_at) >= date_from,
            func.date(GuestProfile.created_at) <= date_to,
        )
    )
    new_guests = new_result.scalar_one()

    # Guests with 2+ visits in the period → returning
    returning_sub = (
        select(GuestVisit.guest_id)
        .join(GuestProfile, GuestVisit.guest_id == GuestProfile.id)
        .where(
            GuestProfile.org_id == org_id,
            func.date(GuestVisit.visited_at) >= date_from,
            func.date(GuestVisit.visited_at) <= date_to,
        )
        .group_by(GuestVisit.guest_id)
        .having(func.count(GuestVisit.id) >= 2)
    ).subquery()
    returning_result = await db.execute(
        select(func.count()).select_from(returning_sub)
    )
    returning_guests = returning_result.scalar_one()

    # Guests with any visit in period
    active_sub = (
        select(GuestVisit.guest_id)
        .join(GuestProfile, GuestVisit.guest_id == GuestProfile.id)
        .where(
            GuestProfile.org_id == org_id,
            func.date(GuestVisit.visited_at) >= date_from,
            func.date(GuestVisit.visited_at) <= date_to,
        )
        .group_by(GuestVisit.guest_id)
    ).subquery()
    active_result = await db.execute(
        select(func.count()).select_from(active_sub)
    )
    active_guests = active_result.scalar_one() or 1

    # Avg visits per guest in period
    avg_visits_result = await db.execute(
        select(func.avg(func.count(GuestVisit.id))).select_from(
            select(GuestVisit.guest_id, func.count(GuestVisit.id).label("cnt"))
            .join(GuestProfile, GuestVisit.guest_id == GuestProfile.id)
            .where(
                GuestProfile.org_id == org_id,
                func.date(GuestVisit.visited_at) >= date_from,
                func.date(GuestVisit.visited_at) <= date_to,
            )
            .group_by(GuestVisit.guest_id)
            .subquery()
        )
    )
    avg_visits = avg_visits_result.scalar_one() or 0

    summary = GuestSummary(
        total_guests=total_guests,
        new_guests_in_period=new_guests,
        returning_guests_in_period=returning_guests,
        return_rate=round(returning_guests / active_guests, 3) if active_guests else 0,
        avg_visits_per_guest=round(float(avg_visits), 1),
    )

    # ── Growth ──
    trunc = _trunc_expr(granularity, GuestProfile.created_at)
    growth_result = await db.execute(
        select(
            cast(trunc, String).label("period"),
            func.count(GuestProfile.id).label("new_guests"),
        ).where(
            GuestProfile.org_id == org_id,
        ).group_by(trunc).order_by(trunc)
    )
    growth = []
    cumulative = 0
    for r in growth_result:
        cumulative += r.new_guests
        growth.append(GuestGrowth(
            period=r.period[:10],
            new_guests=r.new_guests,
            cumulative=cumulative,
        ))

    # ── Top guests ──
    top_result = await db.execute(
        select(
            GuestProfile.id,
            (func.coalesce(GuestProfile.first_name, "") + " " + func.coalesce(GuestProfile.last_name, "")).label("name"),
            func.count(GuestVisit.id).label("visits"),
            func.max(GuestVisit.visited_at).label("last_visit"),
        )
        .join(GuestVisit, GuestVisit.guest_id == GuestProfile.id)
        .where(
            GuestProfile.org_id == org_id,
            func.date(GuestVisit.visited_at) >= date_from,
            func.date(GuestVisit.visited_at) <= date_to,
        )
        .group_by(GuestProfile.id, GuestProfile.first_name, GuestProfile.last_name)
        .order_by(func.count(GuestVisit.id).desc())
        .limit(10)
    )
    top_guests = [
        TopGuest(
            id=str(r.id),
            name=r.name.strip() or "Unknown",
            visits=r.visits,
            last_visit=r.last_visit.strftime("%Y-%m-%d") if r.last_visit else None,
        )
        for r in top_result
    ]

    # ── Tag distribution ──
    tag_result = await db.execute(
        select(
            Tag.id,
            Tag.name,
            Tag.color,
            func.count(guest_tags.c.guest_id).label("cnt"),
        )
        .join(guest_tags, Tag.id == guest_tags.c.tag_id)
        .join(GuestProfile, guest_tags.c.guest_id == GuestProfile.id)
        .where(GuestProfile.org_id == org_id)
        .group_by(Tag.id, Tag.name, Tag.color)
        .order_by(func.count(guest_tags.c.guest_id).desc())
        .limit(15)
    )
    tag_distribution = [
        TagDistribution(
            tag_id=str(r.id),
            tag_name=r.name,
            count=r.cnt,
            color=r.color,
        )
        for r in tag_result
    ]

    return GuestAnalytics(
        summary=summary,
        growth=growth,
        top_guests=top_guests,
        tag_distribution=tag_distribution,
    )


# ─── Operations Analytics ───────────────────────────────────────────────


async def get_operations_analytics(
    db: AsyncSession,
    venue_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> OperationsAnalytics:
    # ── Walk-in ratio ──
    total_result = await db.execute(
        select(
            func.count(Reservation.id).label("total"),
            func.count(case((Reservation.source == "walk_in", 1))).label("walk_ins"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        )
    )
    total_row = total_result.one()
    total_res = total_row.total or 1
    walk_in_ratio = round(total_row.walk_ins / total_res, 3)

    # ── Waitlist stats ──
    wl_result = await db.execute(
        select(
            func.count(WaitlistEntry.id).label("total"),
            func.count(case((WaitlistEntry.status == "seated", 1))).label("seated"),
            func.count(case((WaitlistEntry.status == "cancelled", 1))).label("cancelled"),
            func.count(case((WaitlistEntry.status == "no_show", 1))).label("no_show"),
            func.avg(
                extract("epoch", WaitlistEntry.seated_time) - extract("epoch", WaitlistEntry.check_in_time)
            ).label("avg_wait_seconds"),
        ).where(
            WaitlistEntry.venue_id == venue_id,
            func.date(WaitlistEntry.check_in_time) >= date_from,
            func.date(WaitlistEntry.check_in_time) <= date_to,
        )
    )
    wl = wl_result.one()
    wl_total = wl.total or 1

    waitlist_stats = WaitlistStats(
        total_entries=wl.total,
        seated=wl.seated,
        cancelled=wl.cancelled,
        no_show=wl.no_show,
        avg_wait_minutes=round(float(wl.avg_wait_seconds) / 60, 1) if wl.avg_wait_seconds else None,
    )

    # ── Turn time estimate (time between status becoming 'seated' and 'completed')
    # We approximate this using updated_at of completed reservations minus
    # the reservation time on the same date.
    turn_result = await db.execute(
        select(
            func.avg(
                extract("epoch", Reservation.updated_at)
                - extract("epoch", cast(Reservation.date, String) + " " + cast(Reservation.time, String))
            ).label("avg_turn_seconds"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.status == "completed",
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        )
    )
    turn_row = turn_result.one()
    avg_turn_minutes = (
        round(float(turn_row.avg_turn_seconds) / 60, 0)
        if turn_row.avg_turn_seconds and turn_row.avg_turn_seconds > 0
        else None
    )

    summary = OperationsSummary(
        avg_turn_time_minutes=avg_turn_minutes,
        table_utilization_rate=None,  # Requires time-series table status data; future enhancement
        walk_in_ratio=walk_in_ratio,
        waitlist_conversion_rate=round(wl.seated / wl_total, 3),
        waitlist_abandonment_rate=round((wl.cancelled + wl.no_show) / wl_total, 3),
    )

    # ── Utilization by section ──
    from app.models.floor_plan import Table

    section_result = await db.execute(
        select(
            func.coalesce(Table.section, "Unassigned").label("section"),
            func.coalesce(func.sum(Reservation.party_size), 0).label("covers"),
            func.count(Reservation.id).label("reservation_count"),
        )
        .join(Table, Reservation.table_id == Table.id, isouter=True)
        .where(
            Reservation.venue_id == venue_id,
            Reservation.date >= date_from,
            Reservation.date <= date_to,
            Reservation.status.in_(["seated", "completed"]),
        )
        .group_by(func.coalesce(Table.section, "Unassigned"))
        .order_by(func.sum(Reservation.party_size).desc())
    )
    utilization_by_section = [
        SectionUtilization(
            section=r.section,
            covers=r.covers,
            reservation_count=r.reservation_count,
        )
        for r in section_result
    ]

    # ── Turn time by party size ──
    turn_by_size_result = await db.execute(
        select(
            Reservation.party_size,
            func.avg(
                extract("epoch", Reservation.updated_at)
                - extract("epoch", cast(Reservation.date, String) + " " + cast(Reservation.time, String))
            ).label("avg_turn_seconds"),
        ).where(
            Reservation.venue_id == venue_id,
            Reservation.status == "completed",
            Reservation.date >= date_from,
            Reservation.date <= date_to,
        )
        .group_by(Reservation.party_size)
        .order_by(Reservation.party_size)
    )
    turn_time_by_party_size = [
        TurnTimeByPartySize(
            party_size=r.party_size,
            avg_turn_time_minutes=round(float(r.avg_turn_seconds) / 60, 0) if r.avg_turn_seconds else 0,
        )
        for r in turn_by_size_result
    ]

    return OperationsAnalytics(
        summary=summary,
        utilization_by_section=utilization_by_section,
        turn_time_by_party_size=turn_time_by_party_size,
        waitlist_stats=waitlist_stats,
    )
