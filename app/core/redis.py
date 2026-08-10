from redis.asyncio import Redis

from app.config import settings

_redis = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def get_redis() -> Redis:
    return _redis