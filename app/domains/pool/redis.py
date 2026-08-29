from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.schemas import ZSetCursor
from app.redis.keys import RedisKeys
from app.redis.client import get_redis
from typing import Iterable


class PoolStore:

    def __init__(self):
        self.redis = get_redis()

    def _key(self, pool_name: str) -> str:
        return RedisKeys.pool(pool_name)

    async def _touch(self, pool: BasePool) -> None:
        if pool.refresh_time > 0:
            return

        if pool.idle_age > 0:
            await self.redis.expire(
                self._key(pool.pool_name),
                pool.idle_age,
            )

    def _get_ttl(self, pool: BasePool) -> int | None:
        if pool.refresh_time > 0:
            return pool.refresh_time

        if pool.idle_age > 0:
            return pool.idle_age

        return None

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

    async def get_many_with_cursor(
        self,
        pool: BasePool,
        cursor: ZSetCursor | dict | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[str, float]],ZSetCursor|None]:
        """
        Get highest-ranked posts starting after the specified cursor.
        Returns list of (member/post_id, score) tuples.
        """
        key = self._key(pool.pool_name)

        if isinstance(cursor, ZSetCursor):
            cursor_score = cursor.score
            cursor_member = cursor.member
        elif isinstance(cursor, dict):
            cursor_score = cursor.get("score")
            cursor_member = cursor.get("member")
        else:
            cursor_score = None
            cursor_member = None

        if cursor_score is None or cursor_member is None:
            raw_results = await self.redis.zrevrange(
                key,
                0,
                limit - 1,
                withscores=True,
            )

            await self._touch(pool)

            last = raw_results[-1] if raw_results else None
            new_cursor = ZSetCursor(member=last[0], score=float(last[1])) if last else None

            return [(member, float(score)) for member, score in raw_results], new_cursor

        rank = await self.redis.zrevrank(
            key,
            cursor_member,
        )

        if rank is not None:
            raw_results = await self.redis.zrevrange(
                key,
                rank + 1,
                rank + limit,
                withscores=True,
            )

            await self._touch(pool)

            last = raw_results[-1] if raw_results else None
            new_cursor = ZSetCursor(member=last[0], score=float(last[1])) if last else None

            return [(member, float(score)) for member, score in raw_results], new_cursor

        candidates = await self.redis.zrevrangebyscore(
            key,
            max=cursor_score,
            min="-inf",
            withscores=True,
        )

        results: list[tuple[str, float]] = []

        for member, score in candidates:
            score_val = float(score)

            if (
                score_val < cursor_score
                or (
                    score_val == cursor_score
                    and member < cursor_member
                )
            ):
                results.append((member, score_val))

                if len(results) == limit:
                    break

        await self._touch(pool)

        last = results[-1] if results else None
        new_cursor = ZSetCursor(member=last[0], score=last[1]) if last else None
        
        return results, new_cursor


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