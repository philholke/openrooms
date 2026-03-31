import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.organization import Organization
from app.models.user import User

bearer_scheme = HTTPBearer()

# Ordered from most to least privileged.
ROLE_HIERARCHY: dict[str, int] = {
    "owner": 0,
    "admin": 1,
    "manager": 2,
    "staff": 3,
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials, expected_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    try:
        parsed_id = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
    result = await db.execute(
        select(User).where(User.id == parsed_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_org(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    result = await db.execute(
        select(Organization).where(
            Organization.id == user.org_id, Organization.is_active.is_(True)
        )
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found or inactive",
        )
    return org


def require_role(min_role: str) -> Callable:
    """Return a dependency that checks the user has at least `min_role` privilege."""

    min_level = ROLE_HIERARCHY[min_role]

    async def _check(user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(user.role)
        if user_level is None or user_level > min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{min_role}' or higher",
            )
        return user

    return _check
