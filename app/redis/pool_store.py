from app.redis.client import get_redis
from typing import Iterable


class PoolStore:

    def __init__(self):
        self.redis = get_redis()

    async def add(
        self,
        redis_key: str,
        post_id: str,
        score: float,
    ) -> None:
        """Add or update a post in the pool."""
        await self.redis.zadd(redis_key, {post_id: score})

    async def add_many(
        self,
        redis_key: str,
        posts: Iterable[tuple[str, float]],
    ) -> None:
        """Bulk add/update posts."""
        mapping = {
            post_id: score
            for post_id, score in posts
        }

        if mapping:
            await self.redis.zadd(redis_key, mapping)

    async def top(
        self,
        redis_key: str,
        limit: int = 20,
    ) -> list[str]:
        """Get the highest-ranked post ids."""
        return await self.redis.zrevrange(
            redis_key,
            0,
            limit - 1,
        )

    async def top_with_scores(
        self,
        redis_key: str,
        limit: int = 20,
    ) -> list[tuple[str, float]]:
        """Get highest-ranked posts with scores."""
        return await self.redis.zrevrange(
            redis_key,
            0,
            limit - 1,
            withscores=True,
        )

    async def remove(
        self,
        redis_key: str,
        post_id: str,
    ) -> None:
        await self.redis.zrem(redis_key, post_id)

    async def clear(
        self,
        redis_key: str,
    ) -> None:
        await self.redis.delete(redis_key)

    async def exists(
        self,
        redis_key: str,
    ) -> bool:
        return await self.redis.exists(redis_key) > 0

    async def size(
        self,
        redis_key: str,
    ) -> int:
        return await self.redis.zcard(redis_key)