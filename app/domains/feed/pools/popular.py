from app.domains.feed.pools.base import BasePool
from app.schemas.schemas import PoolPost


class PopularPool(BasePool):
    pool_name = "popular"

    def filter(self, pool_post: PoolPost) -> bool:
        return pool_post.is_active == True

    def score(self, pool_post: PoolPost) -> float:
        return pool_post.engagement_score

    async def get_posts(self, db_repo) -> list[PoolPost]:
        posts = await db_repo.get_popular_posts()
        return [PoolPost.model_validate(post) for post in posts]