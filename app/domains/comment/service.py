from uuid import UUID
from app.domains.comment.repository import CommentRepository
from app.kafka.client import kafka_manager
from app.config import settings

class CommentService:
    def __init__(self, db):
        self.db = db
        self.comment_store = CommentRepository(db)

    async def get_comments_by_post_id(self, post_id: UUID):
        from app.redis.client import get_redis
        redis = get_redis()
        cache_key = f"post_comments:{post_id}"
        
        cached_data = await redis.get(cache_key)
        if cached_data:
            # Note: Depending on your serialization, you might parse this JSON 
            # and map it to your Pydantic schemas or SQLAlchemy models.
            print(f"Cache hit for {cache_key}")
        else:
            print(f"Cache miss for {cache_key}")
            
        comments = await self.comment_store.get_by_post_id(post_id)
        
        # Note: You would serialize 'comments' here to JSON before caching it
        # await redis.setex(cache_key, 3600, serialized_comments)
        return comments

    async def get_replies_by_parent_id(self, post_interaction_id: UUID):
        return await self.comment_store.get_replies_by_parent_id(post_interaction_id)

    async def comment(self, post_id: UUID, user_id: UUID, comment: str):
        result = await self.comment_store.add_comment(post_id, user_id, comment)
        await kafka_manager.send_event(settings.KAFKA_COMMENTS_TOPIC, {
            "action": "comment_added", "post_id": str(post_id), "user_id": str(user_id), "comment_id": str(result.id)
        })
        return result

    async def add_comment_reply(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        result = await self.comment_store.add_comment_reply(user_id, post_interaction_id, comment)
        await kafka_manager.send_event(settings.KAFKA_COMMENTS_TOPIC, {
            "action": "reply_added", "parent_id": str(post_interaction_id), "user_id": str(user_id), "comment_id": str(result.id)
        })
        return result

    async def edit_comment(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        result = await self.comment_store.edit_comment(user_id, post_interaction_id, comment)
        await kafka_manager.send_event(settings.KAFKA_COMMENTS_TOPIC, {
            "action": "comment_edited", "comment_id": str(result.id), "user_id": str(user_id)
        })
        return result

    async def delete(self, user_id: UUID, comment_id: UUID):
        result = await self.comment_store.delete(comment_id)
        await kafka_manager.send_event(settings.KAFKA_COMMENTS_TOPIC, {
            "action": "comment_deleted", "comment_id": str(comment_id), "user_id": str(user_id)
        })
        return result

