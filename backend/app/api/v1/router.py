from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.venues import router as venues_router
from app.api.v1.users import router as users_router
from app.api.v1.access_rules import router as access_rules_router
from app.api.v1.availability import router as availability_router
from app.api.v1.reservations import router as reservations_router
from app.api.v1.waitlist import router as waitlist_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(org_router)
router.include_router(venues_router)
router.include_router(users_router)
router.include_router(access_rules_router)
router.include_router(availability_router)
router.include_router(reservations_router)
router.include_router(waitlist_router)
