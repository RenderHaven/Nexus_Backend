from uuid import UUID

from app.domains.post.repository import PostRepository
from app.domains.post.redis import PostStore
from app.schemas.schemas import Post


class PostStorage:

    def __init__(self, db):
        self.post_store = PostStore()
        self.post_repo = PostRepository(db)

    async def get(self, post_id: UUID) -> Post | None:
        post = await self.post_store.get(str(post_id))

        if post:
            return Post.model_validate(post)

        db_post = await self.post_repo.get_by_id(post_id)

        if not db_post:
            return None

        post = Post.model_validate(db_post)

        await self.post_store.set(
            post.id,
            post.model_dump(mode="json")
        )

        return post

    async def get_many(self, post_ids: list[UUID]) -> list[Post]:
        posts = await self.post_store.get_many([str(pid) for pid in post_ids])

        if posts:
            return [
                Post.model_validate(post)
                for post in posts
            ]

        db_posts = await self.post_repo.posts_by_ids(post_ids)

        if not db_posts:
            return []

        posts = [
            Post.model_validate(post)
            for post in db_posts
        ]

        await self.post_store.set_many(
            [
                post.model_dump(mode="json")
                for post in posts
            ]
        )

        return posts