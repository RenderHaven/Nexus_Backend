from app.domains.feed.pools.base import BasePool
from app.services.post import PostService
from app.redis.pool_store import PoolStore
from app.db.repositories.feed_repo import FeedRepository

from app.domains.feed.pools.popular import PopularPool


class FeedService:

    def __init__(self, db):
        self.db = db

        self.pool_store = PoolStore()
        self.feed_repo = FeedRepository(db)
        self.post_service = PostService(db)

        # Register all pools here
        self.pools = [
            PopularPool(),
        ]

    async def build_pool(self, pool: BasePool):
        """
        Rebuild a specific pool.
        """
        pool_posts = await pool.get_posts(self.feed_repo)

        await self.pool_store.clear(pool.redis_key)

        ranked_posts = []

        for post in pool_posts:
            if not pool.filter(post):
                continue

            ranked_posts.append(
                (
                    str(post.id),
                    pool.score(post),
                )
            )

        await self.pool_store.add_many(
            pool.redis_key,
            ranked_posts,
        )

    async def get_pool_posts(self, pool: BasePool, limit: int = 20):
        """
        Return posts from any pool.
        """
        post_ids = await self.pool_store.top(
            pool.redis_key,
            limit,
        )

        if not post_ids:
            await self.build_pool(pool)

            post_ids = await self.pool_store.top(
                pool.redis_key,
                limit,
            )

        return await self.post_service.get_posts(post_ids)

    async def get_popular_posts(self, limit: int = 100):
        posts = await self.get_pool_posts(
            PopularPool(),
            limit,
        )
        
        return posts