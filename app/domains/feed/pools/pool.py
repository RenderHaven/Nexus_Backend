from app.domains.feed.repository import FeedRepository
from app.domains.feed.redis import PoolStore
from collections import defaultdict
from app.domains.feed.pools.base import BasePool


class PoolStorage:

    def __init__(self,db):
        self.feed_repo = FeedRepository(db)
        self.pool_store = PoolStore()

    async def build(self, pool: BasePool):
        """Build or rebuild a pool."""

        pool_posts = await pool.get_posts(self.feed_repo)

        ranked_posts: dict[str, list[tuple[str, float]]] = defaultdict(list)

        for post in pool_posts:
            if not pool.filter(post):
                continue

            ranked_posts[str(post.category_id)].append(
                (
                    str(post.id),
                    pool.score(post),
                )
            )

        for category_id, posts in ranked_posts.items():
            await self.pool_store.clear(pool.pool_name,category_id)
            await self.pool_store.add_many(
                pool.pool_name,
                posts,
                category_id,
            )
    
    async def get_post_ids_for_category(self,
        pool: BasePool,
        category_id: str | None = None,
        offset: int = 0,
        limit:int=10
    ):
        if not await self.pool_store.exists(pool.pool_name,category_id):
            print("Pool not found, building...")
            await self.build(pool)
        
        post_ids = await self.pool_store.top(
            pool.pool_name,
            offset,
            limit,
            category_id,
        )
        
        if not post_ids:
            return []

        return post_ids

    async def get_posts_ids_by_categories(
        self,
        pool: BasePool,
        total_limit:int,
        categories_probablity:dict[str,(int,float)],
    ):
        post_ids = {}
        for category_id, (offset,probablity) in categories_probablity.items():
            post_ids[category_id]= await self.get_post_ids_for_category(
                pool,category_id,offset,int(total_limit*probablity)
            )
            
        return post_ids