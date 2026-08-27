from app.domains.pool.core.pool_group import PoolGroup
from app.domains.pool.redis import PoolStore
from collections import defaultdict
from app.domains.pool.core.base_pool import BasePool
from app.domains.cursor.service import CursorService


class PoolService:

    def __init__(self):
        self.pool_store = PoolStore()
        self.cursor_svc = CursorService()

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

        await self.pool_store.clear(pool)
        await self.pool_store.create(
            pool,
            ranked_posts,
        )

    async def _get_pool_post_ids(
        self,
        pool: BasePool,
        offset: int = 0,
        limit: int = 10
    ):
        if not await self.pool_store.is_valid(pool):
            await self.build(pool)
        
        post_ids = await self.pool_store.top(
            pool,
            offset,
            limit,
        )
        
        if not post_ids:
            return []

        return post_ids

    async def _get_post_ids_by_offsets(
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

    async def get_post_ids(
        self,
        group_or_pool: PoolGroup | BasePool,
        cursor_key: str | None = None,
        limit: int = 10,
        extra_cursor_data: dict | None = None,
    ):
        cursor = await self.cursor_svc.get_cursor(cursor_key)
        offsets = cursor.get("offsets", {}) if cursor else {}
        
        post_ids, new_offsets = await self._get_post_ids_by_offsets(
            group_or_pool=group_or_pool,
            limit=limit,
            offsets=offsets
        )
        
        offsets.update(new_offsets)
        
        cursor_data = {"offsets": offsets}
        if extra_cursor_data:
            cursor_data.update(extra_cursor_data)
            
        new_cursor_key = await self.cursor_svc.update_cursor(
            cursor_data,
            cursor_key
        )
        
        return post_ids, new_cursor_key