from sqlalchemy import UUID
from app.domains.interaction.repository import PostInteractionRepository
from app.kafka.client import kafka_manager
from app.config import settings

from app.domains.interaction.redis import InteractionRedis

class PostInteractionsService:
    def __init__(self, db):
        self.db = db
        self.post_interaction_store = PostInteractionRepository(db)
        self.redis_store = InteractionRedis()

    async def get_post_interaction(self, post_interaction_id: UUID):
        try:
            return await self.post_interaction_store.get_by_id(post_interaction_id)
        except Exception as e:
            raise e

    async def like(self, post_id: UUID, user_id: UUID):
        try:
            event = {
                "action": "like.created",
                "post_id": str(post_id),
                "user_id": str(user_id)
            }
            await kafka_manager.send_event(settings.KAFKA_INTERACTIONS_TOPIC, event)
            return {"status": "event_published", "action": "like.created", "post_id": post_id, "user_id": user_id}
        except Exception as e:
            raise e

    async def unlike(self, post_id: UUID, user_id: UUID):
        try:
            event = {
                "action": "like.deleted",
                "post_id": str(post_id),
                "user_id": str(user_id)
            }
            await kafka_manager.send_event(settings.KAFKA_INTERACTIONS_TOPIC, event)
            return {"status": "event_published", "action": "like.deleted", "post_id": post_id, "user_id": user_id}
        except Exception as e:
            raise e

    async def build(self):
        from sqlalchemy import select
        from app.db.model import PostReaction

        print("Starting Interaction Redis build...")
        result = await self.db.execute(
            select(PostReaction.post_id, PostReaction.user_id)
        )
        active_likes = result.fetchall()

        likes_by_post = {}
        for post_id, user_id in active_likes:
            likes_by_post.setdefault(str(post_id), []).append(str(user_id))

        pipeline = self.redis_store.redis.pipeline()
        for post_id, users in likes_by_post.items():
            key = self.redis_store._key(post_id)
            temp_key = f"{key}:tmp"
            if users:
                pipeline.sadd(temp_key, *users)
            pipeline.rename(temp_key, key)
        
        await pipeline.execute()
        print(f"Interaction Redis build completed. Restored {len(active_likes)} likes across {len(likes_by_post)} posts.")
