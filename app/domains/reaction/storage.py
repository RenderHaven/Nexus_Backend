from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.reaction.redis import ReactionRedis
from app.domains.reaction.repository import PostInteractionRepository
from app.db.models import PostReaction, ReactionType


class ReactionStorage:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_store = ReactionRedis()
        self.repo = PostInteractionRepository(db)

    async def _build_redis_for_user(self, user_id: UUID | str) -> list[str]:
        """Fetch all active reactions/likes for a user from the database and populate Redis."""
        result = await self.db.execute(
            select(PostReaction.post_id)
            .where(PostReaction.user_id == user_id)
            .where(PostReaction.type== ReactionType.liked)
        )
        post_ids = [str(row[0]) for row in result.fetchall()]

        if post_ids:
            key = self.redis_store._key(user_id)
            temp_key = f"{key}:tmp"
            pipeline = self.redis_store.redis.pipeline()
            pipeline.sadd(temp_key, *post_ids)
            pipeline.rename(temp_key, key)
            await pipeline.execute()

        return post_ids

    async def is_liked(self, post_id: UUID | str, user_id: UUID | str) -> bool:
        """Check if a user liked/reacted to a post, falling back to DB if missing in Redis."""
        exists = await self.redis_store.redis.exists(self.redis_store._key(user_id))
        if exists:
            return await self.redis_store.is_liked(post_id, user_id)

        # Check DB and rebuild
        post_ids = await self._build_redis_for_user(user_id)
        return str(post_id) in post_ids

    async def are_liked(self, post_ids: list[UUID | str], user_id: UUID | str) -> dict[str, bool]:
        """Batch check if a user liked multiple posts."""
        if not post_ids:
            return {}
            
        exists = await self.redis_store.redis.exists(self.redis_store._key(user_id))
        if not exists:
            await self._build_redis_for_user(user_id)
            
        pipeline = self.redis_store.redis.pipeline()
        for post_id in post_ids:
            pipeline.sismember(self.redis_store._key(user_id), str(post_id))
        liked = await pipeline.execute()
        return {str(pid): is_l for pid, is_l in zip(post_ids, liked)}
