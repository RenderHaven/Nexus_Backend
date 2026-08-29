from app.domains.pool.core.schemas import PoolGroup
from app.domains.pool.redis import PoolStore
from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.schemas import ZSetCursor
from app.domains.cursor.service import CursorService


class PoolService:

    def __init__(self):
        self.pool_store = PoolStore()
        self.cursor_svc = CursorService()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    async def build(self, pool: BasePool):
        """Build or rebuild a pool."""

        pool_objects = await pool.get_objects()

        ranked_members: list[tuple[str, float]] = []

        for obj in pool_objects:
            if not pool.filter(obj):
                continue

            # Pool decides how its object is represented as a member.
            member = pool.to_member(obj)

            ranked_members.append(
                (
                    member.model_dump_json(),
                    pool.score(obj),
                )
            )

        await self.pool_store.clear(pool)

        await self.pool_store.create(
            pool,
            ranked_members,
        )

    # ------------------------------------------------------------------
    # Cursor
    # ------------------------------------------------------------------

    async def _get_pool_items_by_cursor(
        self,
        pool: BasePool,
        pool_cursor: dict | ZSetCursor | None = None,
        limit: int = 10,
    ) -> tuple[list[tuple[str, float]], dict | None]:

        if not await self.pool_store.is_valid(pool):
            await self.build(pool)

        items, new_cursor = await self.pool_store.get_many_with_cursor(
            pool=pool,
            cursor=pool_cursor,
            limit=limit,
        )

        return (
            items,
            new_cursor.model_dump(mode="json")
            if new_cursor
            else None,
        )

    # ------------------------------------------------------------------
    # Pool / PoolGroup
    # ------------------------------------------------------------------

    async def _get_pool_members_by_cursors(
        self,
        group_or_pool: PoolGroup | BasePool,
        limit: int = 10,
        cursors: dict[str, dict] | None = None,
    ):
        cursors = cursors or {}

        # --------------------------------------------------------------
        # Single Pool
        # --------------------------------------------------------------

        if isinstance(group_or_pool, BasePool):

            pool = group_or_pool
            pool_cursor = cursors.get(pool.pool_name)

            items, new_cursor = await self._get_pool_items_by_cursor(
                pool=pool,
                pool_cursor=pool_cursor,
                limit=limit,
            )

            member_type = pool.member_type()

            members = [
                member_type.model_validate_json(member_str)
                for member_str, _ in items
            ]

            new_cursors = dict(cursors)

            if new_cursor:
                new_cursors[pool.pool_name] = new_cursor

            return members, new_cursors

        # --------------------------------------------------------------
        # Pool Group
        # --------------------------------------------------------------

        members = []
        new_cursors: dict[str, dict] = dict(cursors)

        for pool_config in group_or_pool.pools:

            pool = (
                pool_config.pool
                if hasattr(pool_config, "pool")
                else pool_config[0]
            )

            weight = (
                pool_config.weight
                if hasattr(pool_config, "weight")
                else pool_config[1]
            )

            pool_cursor = cursors.get(pool.pool_name)

            pool_limit = int(limit * weight)

            if pool_limit <= 0:
                continue

            items, new_cursor = await self._get_pool_items_by_cursor(
                pool=pool,
                pool_cursor=pool_cursor,
                limit=pool_limit,
            )

            member_type = pool.member_type()

            pool_members = [
                member_type.model_validate_json(member_str)
                for member_str, _ in items
            ]

            members.extend(pool_members)

            if new_cursor:
                new_cursors[pool.pool_name] = new_cursor

        return members, new_cursors

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_pool_members(
        self,
        group_or_pool: PoolGroup | BasePool,
        cursor_key: str | None = None,
        limit: int = 10,
        extra_cursor_data: dict | None = None,
    ):
        cursor = await self.cursor_svc.get_cursor(cursor_key)

        cursors = (
            cursor.get("cursors", {})
            if cursor
            else {}
        )

        members, new_cursors = await self._get_pool_members_by_cursors(
            group_or_pool=group_or_pool,
            limit=limit,
            cursors=cursors,
        )

        cursors.update(new_cursors)

        cursor_data = {
            "cursors": cursors,
        }

        if extra_cursor_data:
            cursor_data.update(extra_cursor_data)

        new_cursor_key = await self.cursor_svc.update_cursor(
            cursor_data,
            cursor_key,
        )

        return members, new_cursor_key