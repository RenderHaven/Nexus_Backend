from uuid import UUID

from app.domains.post.repository import PostRepository
from app.domains.post.redis import PostStore
from app.domains.post.schemas import Post


class PostStorage:

    def __init__(self, db):
        self.redis_store = PostStore()
        self.post_repo = PostRepository(db)

    async def get(self, post_id: UUID) -> Post | None:
        post = await self.redis_store.get(str(post_id))

        if post:
            return Post.model_validate(post)

        db_post = await self.post_repo.get_by_id(post_id)

        if not db_post:
            return None

        post = Post.model_validate(db_post)

        await self.redis_store.set(
            post.id,
            post.model_dump(mode="json")
        )

        return post

    async def get_many(self, post_ids: list[UUID]) -> list[Post]:
        if not post_ids:
            return []

        cached_items = await self.redis_store.get_many([str(pid) for pid in post_ids])

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

                await self.redis_store.set_many(new_dicts)

                for p in new_posts:
                    post_map[p.id] = p.model_dump(mode="json")

        results = []
        for pid in post_ids:
            if pid in post_map:
                results.append(Post.model_validate(post_map[pid]))

        return results

    async def add_post(self, post) -> UUID:
        db_post = await self.post_repo.create(post)
        return db_post.id

    async def update(self, post) -> UUID:
        db_post = await self.post_repo.update(post)
        # Delete cache since post was updated and we only have partial data
        await self.redis_store.delete(str(db_post.id))
        return db_post.id

    async def delete(self, post_id: UUID) -> bool:
        db_post = await self.post_repo.get_by_id(post_id)
        if db_post:
            await self.post_repo.delete(db_post)
            await self.redis_store.delete(str(post_id))
            return True
        return False

    async def update_like_count(self, post_id: UUID, change: int) -> bool:
        from sqlalchemy import update
        from app.db.models import Post as DBPost
        
        await self.post_repo.db.execute(
            update(DBPost)
            .where(DBPost.id == post_id)
            .values(like_count=DBPost.like_count + change)
        )

        cached = await self.redis_store.get(str(post_id))
        if cached:
            cached['like_count'] = max(0, cached.get('like_count', 0) + change)
            await self.redis_store.set(str(post_id), cached)
        return True

    async def update_comment_count(self, post_id: UUID, change: int) -> bool:
        from sqlalchemy import update
        from app.db.models import Post as DBPost
        
        await self.post_repo.db.execute(
            update(DBPost)
            .where(DBPost.id == post_id)
            .values(comment_count=DBPost.comment_count + change)
        )

        cached = await self.redis_store.get(str(post_id))
        if cached:
            cached['comment_count'] = max(0, cached.get('comment_count', 0) + change)
            await self.redis_store.set(str(post_id), cached)
        return True