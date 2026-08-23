from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.core.pool_post import PoolPost


class PopularPool(BasePool):
    pool_name = "popular"

    def __init__(self, db_repo):
        super().__init__()
        self.db_repo = db_repo
    
    def filter(self, pool_post: PoolPost) -> bool:
        return pool_post.is_active == True

    def score(self, pool_post: PoolPost) -> float:
        return pool_post.engagement_score

    async def get_posts(self) -> list[PoolPost]:
        posts = await self.db_repo.get_popular_posts(limit=self.pool_size)
        return [PoolPost.model_validate(post) for post in posts]