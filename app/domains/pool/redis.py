from app.domains.pool.core.base_pool import BasePool
from app.redis.keys import RedisKeys
from app.redis.client import get_redis
from typing import Iterable


class PoolStore:

    def __init__(self):
        self.redis = get_redis()

    def _key(self, pool_name: str) -> str:
        return RedisKeys.pool(pool_name)

    def _get_ttl(self, pool: BasePool) -> int | None:
        """
        Return the pool TTL.

        If both refresh_time and idle_age are configured,
        the smaller value is used.

        <= 0 means disabled.
        """
        times = [
            value
            for value in (
                pool.refresh_time,
                pool.idle_age,
            )
            if value > 0
        ]

        return min(times) if times else None

    async def create(
        self,
        pool: BasePool,
        posts: Iterable[tuple[str, float]],
    ) -> None:
        """
        Create a new pool with its initial data and TTL.
        """
        key = self._key(pool.pool_name)

        mapping = {
            post_id: score
            for post_id, score in posts
        }

        if not mapping:
            return

        # Create the sorted set
        await self.redis.zadd(key, mapping)

        # Set expiration once
        ttl = self._get_ttl(pool)

        if ttl is not None:
            await self.redis.expire(key, ttl)

    async def add(
        self,
        pool: BasePool,
        post_id: str,
        score: float,
    ) -> None:
        """Add or update a post without changing the pool TTL."""
        await self.redis.zadd(
            self._key(pool.pool_name),
            {post_id: score},
        )

    async def add_many(
        self,
        pool: BasePool,
        posts: Iterable[tuple[str, float]],
    ) -> None:
        """Bulk add/update posts without changing the pool TTL."""
        mapping = {
            post_id: score
            for post_id, score in posts
        }

        if mapping:
            await self.redis.zadd(
                self._key(pool.pool_name),
                mapping,
            )

    async def top(
        self,
        pool: BasePool,
        offset: int = 0,
        limit: int = 20,
    ) -> list[str]:
        """Get the highest-ranked post ids."""
        return await self.redis.zrevrange(
            self._key(pool.pool_name),
            offset,
            limit + offset - 1,
        )

    async def top_with_scores(
        self,
        pool: BasePool,
        limit: int = 20,
    ) -> list[tuple[str, float]]:
        """Get highest-ranked posts with scores."""
        return await self.redis.zrevrange(
            self._key(pool.pool_name),
            0,
            limit - 1,
            withscores=True,
        )

    async def remove(
        self,
        pool: BasePool,
        post_id: str,
    ) -> None:
        await self.redis.zrem(
            self._key(pool.pool_name),
            post_id,
        )

    async def clear(
        self,
        pool: BasePool,
    ) -> None:
        await self.redis.delete(
            self._key(pool.pool_name),
        )

    async def is_valid(
        self,
        pool: BasePool,
    ) -> bool:
        return await self.redis.exists(
            self._key(pool.pool_name),
        ) > 0

    async def size(
        self,
        pool: BasePool,
    ) -> int:
        return await self.redis.zcard(
            self._key(pool.pool_name)
        )