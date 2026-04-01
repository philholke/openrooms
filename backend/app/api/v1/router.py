from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.venues import router as venues_router
from app.api.v1.users import router as users_router
from app.api.v1.access_rules import router as access_rules_router
from app.api.v1.availability import router as availability_router
from app.api.v1.reservations import router as reservations_router
from app.api.v1.waitlist import router as waitlist_router
from app.api.v1.floor_plans import router as floor_plans_router
from app.api.v1.guests import router as guests_router
from app.api.v1.surveys import router as surveys_router
from app.api.v1.tags import router as tags_router
from app.api.v1.server_assignments import router as server_assignments_router
from app.api.v1.pacing import router as pacing_router
from app.api.v1.reports import router as reports_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(org_router)
router.include_router(venues_router)
router.include_router(users_router)
router.include_router(access_rules_router)
router.include_router(availability_router)
router.include_router(reservations_router)
router.include_router(waitlist_router)
router.include_router(floor_plans_router)
router.include_router(guests_router)
router.include_router(surveys_router)
router.include_router(tags_router)
router.include_router(server_assignments_router)
router.include_router(pacing_router)
router.include_router(reports_router)
