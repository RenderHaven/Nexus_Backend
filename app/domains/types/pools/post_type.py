from app.domains.post.post_pool import BasePostPool
from app.domains.post.schemas import PostPoolObject


class PostTypePool(BasePostPool):

    def __init__(self, post_type: str, repository):
        self.post_type = post_type
        self.repository = repository

        self.pool_name = f"type:{post_type}"

    async def get_posts(self) -> list[PostPoolObject]:
        posts = await self.repository.get_posts_by_type(
            post_type=self.post_type,
            limit=self.pool_size,
        )
        return [PostPoolObject.model_validate(post) for post in posts]

    def filter(self, post: PostPoolObject) -> bool:
        return (
            post.is_active
            and post.type == self.post_type
        )

    def score(self, post: PostPoolObject) -> float:
        return post.created_at.timestamp()