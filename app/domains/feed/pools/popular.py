from app.domains.post.post_pool import BasePostPool
from app.domains.post.schemas import PostPoolObject


class PopularPool(BasePostPool):
    pool_name = "popular"

    def __init__(self, db_repo):
        super().__init__()
        self.db_repo = db_repo
    
    def filter(self, post: PostPoolObject) -> bool:
        return post.is_active == True

    def score(self, post: PostPoolObject) -> float:
        return post.engagement_score

    async def get_posts(self) -> list[PostPoolObject]:
        posts = await self.db_repo.get_popular_posts(limit=self.pool_size)
        return [PostPoolObject.model_validate(post) for post in posts]