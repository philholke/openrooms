"""
arq worker configuration.

Run with:  arq app.core.worker.WorkerSettings

The worker process is independent of the FastAPI app — it creates its own
database session factory and Redis connection. This avoids sharing connection
pools across process boundaries.
"""

import logging

from arq.cron import cron

from app.core.redis import redis_settings
from app.core.tasks import (
    daily_reservation_reminders,
    evaluate_auto_tags_task,
    send_email_task,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Called once when the worker starts. Sets up shared resources."""
    logger.info("Worker starting up — initialising database connection pool")
    # The database session factory is already a module-level singleton in
    # core/database.py, so tasks can import it directly. We store a marker
    # in ctx to confirm startup completed.
    ctx["started"] = True


async def shutdown(ctx: dict) -> None:
    """Called once when the worker shuts down."""
    logger.info("Worker shutting down")


class WorkerSettings:
    """arq worker settings — discovered by `arq app.core.worker.WorkerSettings`."""

    functions = [
        send_email_task,
        evaluate_auto_tags_task,
        daily_reservation_reminders,
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = redis_settings

    # Retry failed jobs up to 3 times with 10s backoff
    max_tries = 3
    job_timeout = 300  # 5 minutes max per task

    # Cron: send reservation reminders daily at 10:00 UTC
    # The task itself handles per-venue timezone conversion.
    cron_jobs = [
        cron(daily_reservation_reminders, hour=10, minute=0),
    ]
