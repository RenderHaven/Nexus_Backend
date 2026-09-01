from uuid import UUID

from app.domains.post.post_pool import BasePostPool
from app.domains.post.schemas import PostPoolObject


class UserPostPool(BasePostPool):

    def __init__(self, user_id: UUID, repository):
        self.user_id = user_id
        self.repository = repository
        # Sliding window: a profile nobody visits stops being rebuilt.
        self.refresh_time = -1
        self.idle_age = 2 * 60 * 60
        self.pool_name = f"user:posts:{user_id}"

    async def get_posts(self) -> list[PostPoolObject]:
        posts = await self.repository.get_posts_ids(
            user_id=self.user_id,
            limit=self.pool_size,
        )
        return [PostPoolObject.model_validate(post) for post in posts]

    def filter(self, post: PostPoolObject) -> bool:
        return post.is_active

    def score(self, post: PostPoolObject) -> float:
        return post.created_at.timestamp()