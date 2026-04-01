import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.limiter import limiter

logger = logging.getLogger(__name__)


# ─── Security Headers Middleware ────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# ─── Global Exception Handler ───────────────────────────────────────────
async def http_exception_handler(_request: Request, exc: HTTPException):
    """Wrap all HTTPExceptions in the standard envelope format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "meta": None,
            "errors": [{"field": None, "message": exc.detail, "code": None}],
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up %s (%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health_check():
    """Liveness check — returns 200 if the process is running."""
    return {"status": "healthy", "project": settings.PROJECT_NAME}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check — verifies database connectivity."""
    from sqlalchemy import text as sa_text
    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as session:
            await session.execute(sa_text("SELECT 1"))
        return {"status": "ready", "project": settings.PROJECT_NAME}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "project": settings.PROJECT_NAME,
                "detail": "Database connection failed",
            },
        )


app.include_router(api_v1_router, prefix="/api/v1")
