from uuid import UUID
from app.domains.cursor.domain import PoolGroupCursor
from app.domains.cursor.service import CursorService
from app.domains.post_type.repository import PostTypeRepository
from app.domains.pool.service import PoolService
from app.domains.post.service import PostService
from app.domains.post_type.enum import PostType
from app.domains.post_type.pools.post_type import PostTypePool

class PostTypeService:
    def __init__(self, db):
        # Services
        self.post_svc = PostService(db)
        self.cursor_svc = CursorService()
        self.pool_service = PoolService()
        
        # Repository
        self.repo = PostTypeRepository(db)

        # Type pools
        self.type_pools: dict[PostType, PostTypePool] = {
            post_type: PostTypePool(
                post_type=post_type,
                repository=self.repo,
            )
            for post_type in PostType
        }

    async def _cursor(
        self,
        cursor_key: str | None = None,
    ) -> PoolGroupCursor | None:
        return await self.cursor_svc.get_pool_group_cursor(cursor_key)

    async def build_pools(self):
        """
        Build all type pools.
        """
        for pool in self.type_pools.values():
            await self.pool_service.build(pool)

    async def get_type_post_ids(
        self,
        post_type: PostType,
        user_id: UUID | None = None,
        cursor_key: str | None = None,
        limit: int = 10,
    ):
        """
        Get post IDs from a specific type pool.
        """
        pool = self.type_pools[post_type]

        feed_cursor = await self._cursor(cursor_key)
        feed_offsets = feed_cursor.offsets if feed_cursor else {}

        post_ids, new_offsets = await self.pool_service.get_post_ids(
            group_or_pool=pool,
            limit=limit,
            offsets=feed_offsets,
        )

        feed_offsets.update(new_offsets)

        new_cursor_key = (
            await self.cursor_svc.update_pool_group_cursor(
                user_id,
                feed_offsets,
                cursor_key,
            )
        )

        return post_ids, new_cursor_key

    async def get_type_posts(
        self,
        post_type: PostType,
        user_id: UUID | None = None,
        cursor_key: str | None = None,
        limit: int = 10,
    ):
        """
        Get hydrated posts for a specific post type.
        """
        pool = self.type_pools[post_type]

        post_ids, new_cursor_key = await self.get_type_post_ids(
            post_type=post_type,
            user_id=user_id,
            cursor_key=cursor_key,
            limit=limit,
        )

        if not post_ids:
            return [], new_cursor_key

        posts = await self.post_svc.get_posts(
            post_ids,
            user_id,
        )

        return posts, new_cursor_key
