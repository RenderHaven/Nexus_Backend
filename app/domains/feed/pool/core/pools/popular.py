from app.domains.feed.pool.core.pools.base import BasePool
from app.schemas.schemas import PostSmall


class PopularPool(BasePool):
    pool_name = "popular"
    
    def filter(self, pool_post: PostSmall) -> bool:
        return pool_post.is_active == True

    def score(self, pool_post: PostSmall) -> float:
        return pool_post.engagement_score

    async def get_posts(self, db_repo) -> list[PostSmall]:
        posts = await db_repo.get_popular_posts(limit=self.pool_size)
        return [PostSmall.model_validate(post) for post in posts]