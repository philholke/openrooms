import logging

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None


def _parse_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into arq RedisSettings."""
    url = settings.REDIS_URL
    # redis://[:password@]host[:port][/database]
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


redis_settings = _parse_redis_settings()


async def get_redis_pool() -> ArqRedis:
    """Return the shared arq Redis pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings)
        logger.info("Redis pool connected to %s:%s", redis_settings.host, redis_settings.port)
    return _pool


async def close_redis_pool() -> None:
    """Close the shared Redis pool."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis pool closed")


async def enqueue(function_name: str, **kwargs) -> str | None:
    """
    Enqueue a background task. Returns the job ID, or None if enqueue fails.

    This is fire-and-forget: failures are logged but never raised,
    so callers (API handlers) are never blocked by Redis issues.
    """
    try:
        pool = await get_redis_pool()
        job = await pool.enqueue_job(function_name, **kwargs)
        if job is not None:
            logger.info("Enqueued task %s (job=%s)", function_name, job.job_id)
            return job.job_id
        logger.warning("Task %s not enqueued (duplicate or queue full)", function_name)
        return None
    except Exception:
        logger.warning("Failed to enqueue task %s", function_name, exc_info=True)
        return None
