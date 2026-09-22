from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Request

from app.config import get_settings

settings = get_settings()

arq_redis_settings = RedisSettings.from_dsn(settings.redis_url)


async def create_arq_pool() -> ArqRedis:
    return await create_pool(arq_redis_settings)


def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool
