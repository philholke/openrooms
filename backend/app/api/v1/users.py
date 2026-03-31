import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_org, get_current_user, require_role
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User
from app.schemas.envelope import Envelope, PaginatedEnvelope, ok, paginated
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=Envelope[UserRead])
async def get_me(user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(user))


@router.get("", response_model=PaginatedEnvelope[UserRead])
async def list_users(
    page: int = 1,
    per_page: int = 25,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    base = select(User).where(User.org_id == org.id, User.is_active.is_(True))

    total_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_result.scalar_one()

    result = await db.execute(
        base.order_by(User.full_name).offset((page - 1) * per_page).limit(per_page)
    )
    users = result.scalars().all()

    return paginated(
        [UserRead.model_validate(u) for u in users],
        page=page,
        per_page=per_page,
        total=total,
    )


@router.post(
    "",
    response_model=Envelope[UserRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: UserCreate,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        org_id=org.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return ok(UserRead.model_validate(user))


@router.get("/{user_id}", response_model=Envelope[UserRead])
async def get_user(
    user_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.org_id == org.id, User.is_active.is_(True)
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return ok(UserRead.model_validate(user))


@router.patch("/{user_id}", response_model=Envelope[UserRead])
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.org_id == org.id, User.is_active.is_(True)
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Only owners can assign the owner role
    if body.role == "owner" and current_user.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners can assign owner role")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)

    await db.flush()
    await db.refresh(target)
    return ok(UserRead.model_validate(target))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")

    result = await db.execute(
        select(User).where(
            User.id == user_id, User.org_id == org.id, User.is_active.is_(True)
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    target.is_active = False
    await db.flush()
