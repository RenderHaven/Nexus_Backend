from app.domains.post.post_pool import BasePostPool
from app.domains.post.schemas import PostPoolObject


class RecentPool(BasePostPool):
    pool_name = "recent"

    

    def __init__(self, db_repo):
        super().__init__()
        self.db_repo = db_repo
        self.refresh_time=2*60*60
    
    def filter(self, post: PostPoolObject) -> bool:
        return post.is_active == True

    def score(self, post: PostPoolObject) -> float:
        return post.created_at.timestamp()

    async def get_posts(self) -> list[PostPoolObject]:
        posts = await self.db_repo.get_recent_posts(limit=self.pool_size)
        return [PostPoolObject.model_validate(post) for post in posts]