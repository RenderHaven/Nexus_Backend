from sqlalchemy import UUID
from app.domains.reaction.repository import PostInteractionRepository
from app.config import settings

from app.domains.reaction.redis import ReactionRedis

class ReactionService:
    def __init__(self, db):
        self.db = db
        self.post_interaction_store = PostInteractionRepository(db)
        self.redis_store = ReactionRedis()

    async def get_post_interaction(self, post_interaction_id: UUID):
        return await self.post_interaction_store.get_by_id(post_interaction_id)
        
    async def like(self, post_id: UUID, user_id: UUID):
        reaction = await self.post_interaction_store.update_like(post_id, user_id, True, commit=True)
        if reaction:
            await self.redis_store.update(str(post_id), str(user_id), like=True)
            from app.domains.post.service import PostService
            post_svc = PostService(self.db)
            await post_svc.post_store.update_like_count(post_id, 1)

        return {"status": "success", "action": "like.created", "post_id": str(post_id), "user_id": str(user_id)}

    async def unlike(self, post_id: UUID, user_id: UUID):
        reaction = await self.post_interaction_store.update_like(post_id, user_id, False, commit=True)
        if reaction:
            await self.redis_store.update(str(post_id), str(user_id), like=False)
            from app.domains.post.service import PostService
            post_svc = PostService(self.db)
            await post_svc.post_store.update_like_count(post_id, -1)
            
        return {"status": "success", "action": "like.deleted", "post_id": str(post_id), "user_id": str(user_id)}

    async def update_db_batch(self, batch_messages):
        """Update DB with a batch of reaction messages."""
        count = 0
        from collections import defaultdict
        net_likes = defaultdict(int)
        
        for tp, messages in batch_messages.items():
            for msg in messages:
                data = msg.value
                action = data.get("action")
                post_id_str = data.get("post_id")
                post_id = UUID(post_id_str)
                user_id = UUID(data.get("user_id"))

                if action == "like.created":
                    await self.post_interaction_store.update_like(post_id, user_id, True, commit=False)
                    net_likes[post_id_str] += 1
                elif action == "like.deleted":
                    await self.post_interaction_store.update_like(post_id, user_id, False, commit=False)
                    net_likes[post_id_str] -= 1
                count += 1
        
        await self.db.commit()

        # Update like counts sequentially in DB and Redis
        if net_likes:
            from app.domains.post.service import PostService
            post_svc = PostService(self.db)
            for post_id_str, change in net_likes.items():
                if change != 0:
                    await post_svc.post_store.update_like_count(UUID(post_id_str), change)
                    
        return count

    async def update_redis_batch(self, batch_messages):
        """Update Redis with a batch of reaction messages."""
        for tp, messages in batch_messages.items():
            for msg in messages:
                data = msg.value
                action = data.get("action")
                post_id = data.get("post_id")
                user_id = data.get("user_id")

                if action == "like.created":
                    await self.redis_store.update(post_id, user_id, like=True)
                elif action == "like.deleted":
                    await self.redis_store.update(post_id, user_id, like=False)

    async def build(self):
        from sqlalchemy import select
        from app.db.models import PostReaction

        print("Starting Reaction Redis build...")
        result = await self.db.execute(
            select(PostReaction.post_id, PostReaction.user_id)
        )
        active_likes = result.fetchall()

        likes_by_user = {}
        for post_id, user_id in active_likes:
            likes_by_user.setdefault(str(user_id), []).append(str(post_id))

        pipeline = self.redis_store.redis.pipeline()
        for user_id, posts in likes_by_user.items():
            key = self.redis_store._key(user_id)
            temp_key = f"{key}:tmp"
            if posts:
                pipeline.sadd(temp_key, *posts)
            pipeline.rename(temp_key, key)
        
        await pipeline.execute()
        print(f"Reaction Redis build completed. Restored {len(active_likes)} likes across {len(likes_by_user)} users.")
