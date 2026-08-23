from app.domains.pool.core.pool_group import PoolGroup
from app.domains.pool.redis import PoolStore
from collections import defaultdict
from app.domains.pool.core.base_pool import BasePool


class PoolService:

    def __init__(self):
        self.pool_store = PoolStore()

    async def build(self, pool: BasePool):
        """Build or rebuild a pool."""

        pool_posts = await pool.get_posts()

        ranked_posts: list[tuple[str, float]] = []

        for post in pool_posts:
            if not pool.filter(post):
                continue

            ranked_posts.append(
                (
                    str(post.id),
                    pool.score(post),
                )
            )

        await self.pool_store.clear(pool.pool_name)
        await self.pool_store.add_many(
            pool.pool_name,
            ranked_posts,
        )

    async def _get_pool_post_ids(
        self,
        pool: BasePool,
        offset: int = 0,
        limit: int = 10
    ):
        if not await self.pool_store.exists(pool.pool_name):
            await self.build(pool)
        
        post_ids = await self.pool_store.top(
            pool.pool_name,
            offset,
            limit,
        )
        
        if not post_ids:
            return []

        return post_ids

    async def get_post_ids(
        self,
        group_or_pool: PoolGroup | BasePool,
        limit: int = 10,
        offsets: dict[str, int] | None = None,
    ):
        offsets = offsets or {}

        if isinstance(group_or_pool, BasePool):
            pool = group_or_pool
            offset = offsets.get(pool.pool_name, 0)
            
            ids = await self._get_pool_post_ids(
                pool=pool,
                offset=offset,
                limit=limit,
            )
            
            new_offsets = {pool.pool_name: offset + len(ids)}
            return ids, new_offsets

        # Handle PoolGroup
        post_ids: list[str] = []
        new_offsets: dict[str, int] = {}

        for pool, probability in group_or_pool.pools:
            pool_offset = offsets.get(pool.pool_name, 0)

            pool_limit = int(limit * probability)

            if pool_limit <= 0:
                continue

            ids = await self._get_pool_post_ids(
                pool=pool,
                offset=pool_offset,
                limit=pool_limit,
            )

            post_ids.extend(ids)

            new_offsets[pool.pool_name] = (
                pool_offset + len(ids)
            )

        return post_ids, new_offsets

