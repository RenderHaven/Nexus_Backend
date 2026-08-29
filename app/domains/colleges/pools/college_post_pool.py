from uuid import UUID
from app.domains.post.post_pool import BasePostPool
from app.domains.post.schemas import PostPoolObject

class CollegePostPool(BasePostPool):
    def __init__(self, college_id: UUID, repository):
        self.college_id = college_id
        self.repository = repository
        self.pool_name = f"college:posts:{college_id}"

    async def get_posts(self) -> list[PostPoolObject]:
        posts = await self.repository.get_posts_ids(
            college_id=self.college_id,
            limit=self.pool_size,
        )
        return [PostPoolObject.model_validate(post) for post in posts]

    def filter(self, post: PostPoolObject) -> bool:
        return post.is_active

    def score(self, post: PostPoolObject) -> float:
        return post.created_at.timestamp()
