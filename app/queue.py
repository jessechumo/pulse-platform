import logging

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import HTTPException, Request

from app.config import get_settings

logger = logging.getLogger("pulse.queue")

settings = get_settings()

arq_redis_settings = RedisSettings.from_dsn(settings.redis_url)

# Used only by the lazy per-request recovery path in require_arq_pool: fails
# fast (no retries) instead of repeating the startup pool's multi-second
# retry-with-backoff on every single request while Redis is still down.
_fast_fail_redis_settings = RedisSettings.from_dsn(settings.redis_url)
_fast_fail_redis_settings.conn_retries = 0


async def create_arq_pool() -> ArqRedis | None:
    try:
        return await create_pool(arq_redis_settings)
    except Exception:
        # Redis being unreachable at boot shouldn't take the whole app down
        # with it -- /ready already reports redis as unreachable via
        # check_redis(), which is how Kubernetes is meant to find out.
        # Crashing here instead turns that into a crash loop.
        logger.exception("could not connect to redis for the job queue at startup")
        return None


async def require_arq_pool(request: Request) -> ArqRedis:
    pool = request.app.state.arq_pool
    if pool is not None:
        return pool

    try:
        pool = await create_pool(_fast_fail_redis_settings)
    except Exception:
        raise HTTPException(status_code=503, detail="job queue unavailable") from None

    request.app.state.arq_pool = pool
    return pool
