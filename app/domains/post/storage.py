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

        await self.post_store.add_active_post(str(post.id))
        from app.domains.interaction.storage import InteractionStorage
        interaction_store = InteractionStorage(self.post_repo.db)
        await interaction_store._build_redis_for_post(post.id)

        return post

    async def get_many(self, post_ids: list[UUID]) -> list[Post]:
        if not post_ids:
            return []

        cached_items = await self.post_store.get_many([str(pid) for pid in post_ids])

        post_map: dict[UUID, dict] = {}
        missing_ids: list[UUID] = []

        for pid, item in zip(post_ids, cached_items):
            if item is not None:
                post_map[pid] = item
            else:
                missing_ids.append(pid)

        if missing_ids:
            db_posts = await self.post_repo.posts_by_ids(missing_ids)
            if db_posts:
                new_posts = [Post.model_validate(p) for p in db_posts]
                new_dicts = [p.model_dump(mode="json") for p in new_posts]

                await self.post_store.set_many(new_dicts)

                from app.domains.interaction.storage import InteractionStorage
                interaction_store = InteractionStorage(self.post_repo.db)

                for p in new_posts:
                    post_map[p.id] = p.model_dump(mode="json")
                    await self.post_store.add_active_post(str(p.id))
                    await interaction_store._build_redis_for_post(p.id)

        results = []
        for pid in post_ids:
            if pid in post_map:
                results.append(Post.model_validate(post_map[pid]))

        return results

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