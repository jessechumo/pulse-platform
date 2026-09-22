import logging

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger("pulse.cache")

settings = get_settings()

# Same fail-fast reasoning as the DB engine: a readiness check shouldn't
# hang waiting for a dead Redis.
redis_client = redis.from_url(
    settings.redis_url,
    socket_connect_timeout=2,
    socket_timeout=2,
)


async def check_redis() -> bool:
    try:
        await redis_client.ping()
        return True
    except Exception:
        logger.exception("redis readiness check failed")
        return False
