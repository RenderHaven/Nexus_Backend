from uuid import UUID
from app.domains.cursor.service import CursorService
from app.domains.types.repository import PostTypeRepository
from app.domains.pool.service import PoolService
from app.domains.post.service import PostService
from app.domains.types.enum import PostType
from app.domains.types.pools.post_type import PostTypePool

class PostTypeService:
    def __init__(self, db):
        # Services
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



    async def build_pools(self):
        """
        Build all type pools.
        """
        for pool in self.type_pools.values():
            await self.pool_service.build(pool)

    async def get_pool_members(
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

        extra_data = {"user_id": str(user_id)} if user_id else None

        post_items, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data=extra_data
        )

        return post_items, new_cursor_key

