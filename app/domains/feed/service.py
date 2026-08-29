import random
from collections import defaultdict
from uuid import UUID

from app.domains.categories.service import CategoryService
from app.domains.cursor.service import CursorService
from app.domains.feed.pools.popular import PopularPool
from app.domains.feed.pools.recent import RecentPool
from app.domains.feed.repository import FeedRepository
from app.domains.post.post_pool import BasePostPool
from app.domains.pool.core.schemas import PoolGroup
from app.domains.pool.service import PoolService
from app.domains.post.service import PostService
from app.domains.user.service import UserService

class FeedService:

    def __init__(self, db):
        self.feed_size = 100

        # Services
        self.post_svc = PostService(db)
        self.user_svc = UserService(db)
        self.category_svc = CategoryService(db)

        # Repository
        self.feed_repo = FeedRepository(db)

        # Pool infrastructure
        self.pool_service = PoolService()

        # Feed cursor
        self.cursor_svc = CursorService()

        # Feed groups
        self.feed_grps: dict[str, BasePostPool | PoolGroup] = {
            "popular": PopularPool(db_repo=self.feed_repo),
            "recent" : RecentPool(db_repo=self.feed_repo),
        }

    # ------------------------------------------------------------------
    # Cursor
    # ------------------------------------------------------------------

    async def get_feed_cursor(
        self,
        cursor_key: str | None = None,
    ) -> dict | None:
        return await self.cursor_svc.get_cursor(cursor_key)

    # ------------------------------------------------------------------
    # Build pools
    # ------------------------------------------------------------------

    async def build_pools(self):
        """
        Build all feed groups.
        """

        for grp in self.feed_grps.values():
            if isinstance(grp, PoolGroup):
                for pool_config in grp.pools:
                    await self.pool_service.build(pool_config.pool)
            else:
                await self.pool_service.build(grp)

    def get_feed_groups(self) -> list[str]:
        """
        Get all available feed group names.
        """
        return list(self.feed_grps.keys())



    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    async def _get_dummy_preferences(self) -> dict[str, float]:

        categories = await self.category_svc.get_all_categories()

        preferences = {}

        for category in categories:
            preferences[str(category.id)] = random.random()

        return preferences

    async def get_preferences(
        self,
        user_id: UUID | None = None,
    ) -> dict[str, float]:

        preferences = (
            await self.user_svc.get_category_preferences(
                user_id
            )
        )

        if not preferences:
            return await self._get_dummy_preferences()

        print(preferences)
        return preferences

    # ------------------------------------------------------------------
    # Normal feed IDs
    # ------------------------------------------------------------------

    async def get_pool_members(
        self,
        grp_name: str="popular",
        user_id: UUID | None = None,
        cursor_key: str | None = None,
    ):
        """
        Get post IDs for a feed group.
        """

        feed_grp = self.feed_grps.get(grp_name)
        
        if not feed_grp:
            return [], cursor_key

        extra_data = {"user_id": str(user_id)} if user_id else None

        pool_members, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=feed_grp,
            cursor_key=cursor_key,
            limit=self.feed_size,
            extra_cursor_data=extra_data
        )

        return pool_members, new_cursor_key

    # ------------------------------------------------------------------
    # Normal feed posts
    # ------------------------------------------------------------------

    async def get_posts(
        self,
        grp_name: str,
        user_id: UUID | None = None,
        cursor_key: str | None = None,
    ):
        """
        Get hydrated posts from the normal feed.
        """

        pool_members, new_cursor_key = await self.get_pool_members(
            grp_name,
            user_id,
            cursor_key,
        )

        if not pool_members:
            return [], new_cursor_key

        ids_only = [m.id for m in pool_members]
        posts = await self.post_svc.get_posts(
            ids_only,
            user_id,
        )

        return posts, new_cursor_key