from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.core.pool_post import PoolPost


class PostTypePool(BasePool):

    def __init__(self, post_type: str, repository):
        self.post_type = post_type
        self.repository = repository

        self.pool_name = f"type:{post_type}"

    async def get_posts(self) -> list[PoolPost]:
        posts = await self.repository.get_posts_by_type(
            post_type=self.post_type,
            limit=self.pool_size,
        )
        return [PoolPost.model_validate(post) for post in posts]

    def filter(self, post: PoolPost) -> bool:
        return (
            post.is_active
            and post.type == self.post_type
        )

    def score(self, post: PoolPost) -> float:
        return post.created_at.timestamp()