from uuid import UUID

from app.domains.pool.core.base_pool import BasePool
from app.domains.post.schemas import PoolPost


class UserPostPool(BasePool):

    def __init__(self, user_id: UUID, repository):
        self.user_id = user_id
        self.repository = repository
        self.idle_age=2*60*60
        self.pool_name = f"user:posts:{user_id}"

    async def get_posts(self) -> list[PoolPost]:
        posts = await self.repository.get_posts_ids(
            user_id=self.user_id,
            limit=self.pool_size,
        )
        return [PoolPost.model_validate(post) for post in posts]

    def filter(self, post: PoolPost) -> bool:
        return post.is_active

    def score(self, post: PoolPost) -> float:
        return post.created_at.timestamp()