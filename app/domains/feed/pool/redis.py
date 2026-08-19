from app.redis.keys import RedisKeys
from app.redis.client import get_redis
from typing import Iterable


class PoolStore:

    def __init__(self):
        self.redis = get_redis()

    def _key(self, pool_name: str, category_id: str | None = None) -> str:
        return RedisKeys.pool(pool_name, category_id)

    async def add(
        self,
        pool_name:str,
        post_id: str,
        score: float,
        category_id: str|None=None,
    ) -> None:
        """Add or update a post in the pool."""
        await self.redis.zadd(self._key(pool_name, category_id), {post_id: score})

    async def add_many(
        self,
        pool_name:str,
        posts: Iterable[tuple[str, float]],
        category_id: str|None=None,
    ) -> None:
        """Bulk add/update posts."""
        mapping = {
            post_id: score
            for post_id, score in posts
        }

        if mapping:
            await self.redis.zadd(self._key(pool_name, category_id), mapping)

    async def top(
        self,
        pool_name:str,
        offset:int = 0,
        limit: int = 20,
        category_id: str|None=None,
    ) -> list[str]:
        """Get the highest-ranked post ids."""
        return await self.redis.zrevrange(
            self._key(pool_name, category_id),
            offset,
            limit+offset-1,
        )

    async def top_with_scores(
        self,   
        pool_name:str,
        limit: int = 20,
        category_id: str|None=None,
    ) -> list[tuple[str, float]]:
        """Get highest-ranked posts with scores."""
        return await self.redis.zrevrange(
            self._key(pool_name, category_id),
            0,
            limit - 1,
            withscores=True,
        )

    async def remove(
        self,
        pool_name:str,
        post_id: str,
        category_id: str|None=None,
    ) -> None:
        await self.redis.zrem(self._key(pool_name, category_id), post_id)

    async def clear(
        self,
        pool_name:str,
        category_id: str|None=None,
    ) -> None:
        await self.redis.delete(self._key(pool_name, category_id))

    async def exists(
        self,
        pool_name:str,
        category_id: str|None=None,
    ) -> bool:
        return await self.redis.exists(self._key(pool_name, category_id)) > 0

    async def size(
        self,
        pool_name:str,
        category_id: str|None=None,
    ) -> int:
        return await self.redis.zcard(self._key(pool_name, category_id))