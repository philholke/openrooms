import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.envelope import Envelope, ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=Envelope[TokenResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check email uniqueness (only among active users — soft-deleted emails can be reused)
    existing = await db.execute(
        select(User).where(User.email == body.email, User.is_active.is_(True))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Check slug uniqueness
    existing_org = await db.execute(
        select(Organization).where(
            Organization.slug == body.org_slug, Organization.is_active.is_(True)
        )
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Organization slug already taken")

    try:
        org = Organization(name=body.org_name, slug=body.org_slug)
        db.add(org)
        await db.flush()

        user = User(
            org_id=org.id,
            email=body.email,
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
            role="owner",
        )
        db.add(user)
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Email or organization slug already taken",
        )

    logger.info("New org '%s' registered by %s", org.slug, body.email)

    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return ok(tokens)


@router.post("/login", response_model=Envelope[TokenResponse])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        logger.warning("Failed login attempt for %s", body.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    logger.info("User %s logged in", body.email)
    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return ok(tokens)


@router.post("/refresh", response_model=Envelope[TokenResponse])
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(body.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    user_id = payload["sub"]
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return ok(tokens)
