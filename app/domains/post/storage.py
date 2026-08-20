from uuid import UUID

from app.domains.post.repository import PostRepository
from app.domains.post.redis import PostStore
from app.schemas.schemas import Post


class PostStorage:

    def __init__(self, db):
        self.post_store = PostStore()
        self.post_repo = PostRepository(db)

    async def get(self, post_id: UUID) -> Post | None:
        print("hii")
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

        await self.post_store.add_active_post(str(post.id))
        from app.domains.interaction.storage import InteractionStorage
        interaction_store = InteractionStorage(self.post_repo.db)
        await interaction_store._build_redis_for_post(post.id)

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

        from app.domains.interaction.storage import InteractionStorage
        interaction_store = InteractionStorage(self.post_repo.db)
        for post in posts:
            await self.post_store.add_active_post(str(post.id))
            await interaction_store._build_redis_for_post(post.id)

        return posts

    async def update(self, post) -> Post:
        db_post = await self.post_repo.update(post)
        validated = Post.model_validate(db_post)
        await self.post_store.set(str(validated.id), validated.model_dump(mode="json"))
        return validated

    async def delete(self, post_id: UUID) -> bool:
        db_post = await self.post_repo.get_by_id(post_id)
        if db_post:
            await self.post_repo.delete(db_post)
            await self.post_store.delete(str(post_id))
            await self.post_store.remove_active_post(str(post_id))
            from app.domains.interaction.storage import InteractionStorage
            interaction_store = InteractionStorage(self.post_repo.db)
            await interaction_store.redis_store.redis.delete(interaction_store.redis_store._key(post_id))
            return True
        return False