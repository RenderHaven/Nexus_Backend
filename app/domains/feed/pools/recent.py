from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.core.pool_post import PoolPost


class RecentPool(BasePool):
    pool_name = "recent"

    

    def __init__(self, db_repo):
        super().__init__()
        self.db_repo = db_repo
        self.refresh_time=2*60*60
    
    def filter(self, post: PoolPost) -> bool:
        return post.is_active == True

    def score(self, post: PoolPost) -> float:
        return post.created_at.timestamp()

    async def get_posts(self) -> list[PoolPost]:
        posts = await self.db_repo.get_recent_posts(limit=self.pool_size)
        return [PoolPost.model_validate(post) for post in posts]