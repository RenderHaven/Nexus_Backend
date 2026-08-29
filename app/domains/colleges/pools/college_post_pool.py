from uuid import UUID
from app.domains.pool.core.base_pool import BasePool
from app.domains.post.schemas import PoolPost

class CollegePostPool(BasePool):
    def __init__(self, college_id: UUID, repository):
        self.college_id = college_id
        self.repository = repository
        self.pool_name = f"college:posts:{college_id}"

    async def get_posts(self) -> list[PoolPost]:
        posts = await self.repository.get_posts_ids(
            college_id=self.college_id,
            limit=self.pool_size,
        )
        return [PoolPost.model_validate(post) for post in posts]

    def filter(self, post: PoolPost) -> bool:
        return post.is_active

    def score(self, post: PoolPost) -> float:
        return post.created_at.timestamp()
