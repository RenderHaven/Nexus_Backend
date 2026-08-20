from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.interaction.redis import InteractionRedis
from app.domains.interaction.repository import PostInteractionRepository
from app.db.model import PostReaction, Post


class InteractionStorage:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_store = InteractionRedis()
        self.repo = PostInteractionRepository(db)

    async def _build_redis_for_post(self, post_id: UUID | str) -> list[str]:
        """Fetch all active reactions/likes for a post from the database and populate Redis."""
        result = await self.db.execute(
            select(PostReaction.user_id)
            .where(PostReaction.post_id == post_id)
        )
        user_ids = [str(row[0]) for row in result.fetchall()]

        if user_ids:
            key = self.redis_store._key(post_id)
            temp_key = f"{key}:tmp"
            pipeline = self.redis_store.redis.pipeline()
            pipeline.sadd(temp_key, *user_ids)
            pipeline.rename(temp_key, key)
            await pipeline.execute()

        return user_ids

    async def get_likes_count(self, post_id: UUID | str) -> int:
        """Get the total number of likes for a post, falling back to DB if missing in Redis."""
        exists = await self.redis_store.redis.exists(self.redis_store._key(post_id))
        if exists:
            return await self.redis_store.get_count(post_id)

        # Check DB and rebuild
        user_ids = await self._build_redis_for_post(post_id)
        return len(user_ids)

    async def is_liked(self, post_id: UUID | str, user_id: UUID | str) -> bool:
        """Check if a user liked/reacted to a post, falling back to DB if missing in Redis."""
        exists = await self.redis_store.redis.exists(self.redis_store._key(post_id))
        if exists:
            return await self.redis_store.is_liked(post_id, user_id)

        # Check DB and rebuild
        user_ids = await self._build_redis_for_post(post_id)
        return str(user_id) in user_ids

    async def get_likes_counts(self, post_ids: list[UUID | str]) -> dict[str, int]:
        """Batch fetch like counts for multiple posts."""
        if not post_ids:
            return {}
        pipeline = self.redis_store.redis.pipeline()
        for post_id in post_ids:
            pipeline.scard(self.redis_store._key(post_id))
        counts = await pipeline.execute()
        return {str(pid): count for pid, count in zip(post_ids, counts)}

    async def are_liked(self, post_ids: list[UUID | str], user_id: UUID | str) -> dict[str, bool]:
        """Batch check if a user liked multiple posts."""
        if not post_ids:
            return {}
        pipeline = self.redis_store.redis.pipeline()
        for post_id in post_ids:
            pipeline.sismember(self.redis_store._key(post_id), str(user_id))
        liked = await pipeline.execute()
        return {str(pid): is_l for pid, is_l in zip(post_ids, liked)}
