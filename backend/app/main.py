import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings

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
    return {"status": "healthy", "project": settings.PROJECT_NAME}


app.include_router(api_v1_router, prefix="/api/v1")
