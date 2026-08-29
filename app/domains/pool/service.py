from app.domains.pool.core.pool_group import PoolGroup
from app.domains.pool.redis import PoolStore
from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.schemas import ZSetCursor, PoolMember
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

            member = PoolMember(
                id=post.id,
                name=post.name,
                type=post.type,
                created_at=post.created_at
            )

            ranked_posts.append(
                (
                    member.model_dump_json(),
                    pool.score(post),
                )
            )

        await self.pool_store.clear(pool)
        await self.pool_store.create(
            pool,
            ranked_posts,
        )

    async def _get_pool_posts_by_cursor(
        self,
        pool: BasePool,
        pool_cursor: dict | ZSetCursor | None = None,
        limit: int = 10,
    ) -> tuple[list[tuple[str, float]],dict|None]:
        if not await self.pool_store.is_valid(pool):
            await self.build(pool)

        items, new_cursor = await self.pool_store.get_many_with_cursor(
            pool=pool,
            cursor=pool_cursor,
            limit=limit,
        )

        return items, new_cursor.model_dump(mode="json") if new_cursor else None

    async def _get_pool_members_by_cursors(
        self,
        group_or_pool: PoolGroup | BasePool,
        limit: int = 10,
        cursors: dict[str, dict] | None = None,
    ):
        cursors = cursors or {}

        if isinstance(group_or_pool, BasePool):
            pool = group_or_pool
            pool_cursor = cursors.get(pool.pool_name)

            items,new_cursor = await self._get_pool_posts_by_cursor(
                pool=pool,
                pool_cursor=pool_cursor,
                limit=limit,
            )

            members = [PoolMember.model_validate_json(member_str) for member_str, _ in items]
            new_cursors = dict(cursors)
            if new_cursor:
                new_cursors[pool.pool_name] = new_cursor

            return members, new_cursors

        # Handle PoolGroup
        members: list[PoolMember] = []
        new_cursors: dict[str, dict] = dict(cursors)

        for pool_config in group_or_pool.pools:
            pool = pool_config.pool if hasattr(pool_config, "pool") else pool_config[0]
            weight = pool_config.weight if hasattr(pool_config, "weight") else pool_config[1]

            pool_cursor = cursors.get(pool.pool_name)
            pool_limit = int(limit * weight)

            if pool_limit <= 0:
                continue

            items,new_cursor = await self._get_pool_posts_by_cursor(
                pool=pool,
                pool_cursor=pool_cursor,
                limit=pool_limit,
            )

            pool_members = [PoolMember.model_validate_json(member_str) for member_str, _ in items]
            members.extend(pool_members)

            if new_cursor:
                new_cursors[pool.pool_name] = new_cursor

        return members, new_cursors

    async def get_pool_members(
        self,
        group_or_pool: PoolGroup | BasePool,
        cursor_key: str | None = None,
        limit: int = 10,
        extra_cursor_data: dict | None = None,
    ):
        cursor = await self.cursor_svc.get_cursor(cursor_key)
        cursors = cursor.get("cursors", {}) if cursor else {}

        members, new_cursors = await self._get_pool_members_by_cursors(
            group_or_pool=group_or_pool,
            limit=limit,
            cursors=cursors,
        )

        cursors.update(new_cursors)

        cursor_data = {"cursors": cursors}
        if extra_cursor_data:
            cursor_data.update(extra_cursor_data)

        new_cursor_key = await self.cursor_svc.update_cursor(
            cursor_data,
            cursor_key,
        )

        return members, new_cursor_key