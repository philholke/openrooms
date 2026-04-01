"""
ServerAssignment service — manage server-to-section assignments per shift.
"""

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.server_assignment import ServerAssignment
from app.models.user import User
from app.models.venue import Venue
from app.schemas.server_assignment import ServerAssignmentCreate, ServerAssignmentRead


async def list_assignments(
    db: AsyncSession,
    venue_id: uuid.UUID,
    for_date: date,
) -> list[ServerAssignmentRead]:
    result = await db.execute(
        select(ServerAssignment)
        .options(selectinload(ServerAssignment.user))
        .where(
            ServerAssignment.venue_id == venue_id,
            ServerAssignment.date == for_date,
            ServerAssignment.is_active.is_(True),
        )
        .order_by(ServerAssignment.section)
    )
    assignments = result.scalars().all()
    return [
        ServerAssignmentRead(
            id=a.id,
            venue_id=a.venue_id,
            date=a.date,
            section=a.section,
            user_id=a.user_id,
            user_name=a.user.full_name if a.user else None,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in assignments
    ]


async def upsert_assignment(
    db: AsyncSession,
    venue_id: uuid.UUID,
    data: ServerAssignmentCreate,
    org_id: uuid.UUID,
) -> ServerAssignmentRead:
    # Verify user exists, is active, and belongs to the same org as the venue
    user_result = await db.execute(
        select(User).where(User.id == data.user_id, User.is_active.is_(True))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.org_id != org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User does not belong to this organization")

    # Check for existing assignment for this venue+date+section
    result = await db.execute(
        select(ServerAssignment).where(
            ServerAssignment.venue_id == venue_id,
            ServerAssignment.date == data.date,
            ServerAssignment.section == data.section,
            ServerAssignment.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.user_id = data.user_id
        await db.flush()
        await db.refresh(existing, ["user"])
        return ServerAssignmentRead(
            id=existing.id,
            venue_id=existing.venue_id,
            date=existing.date,
            section=existing.section,
            user_id=existing.user_id,
            user_name=existing.user.full_name if existing.user else None,
            is_active=existing.is_active,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )

    assignment = ServerAssignment(
        venue_id=venue_id,
        date=data.date,
        section=data.section,
        user_id=data.user_id,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment, ["user"])
    return ServerAssignmentRead(
        id=assignment.id,
        venue_id=assignment.venue_id,
        date=assignment.date,
        section=assignment.section,
        user_id=assignment.user_id,
        user_name=assignment.user.full_name if assignment.user else None,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


async def delete_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(ServerAssignment).where(
            ServerAssignment.id == assignment_id,
            ServerAssignment.is_active.is_(True),
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    # Verify the assignment's venue belongs to the requesting org
    venue_result = await db.execute(
        select(Venue).where(Venue.id == assignment.venue_id)
    )
    venue = venue_result.scalar_one_or_none()
    if venue is None or venue.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    assignment.is_active = False
    await db.flush()
