from sqlalchemy import UUID
from app.domains.interaction.repository import PostInteractionRepository

class PostInteractionsService:
    def __init__(self, db):
        self.db = db
        self.post_interaction_store = PostInteractionRepository(db)

    async def get_post_interaction(self, post_interaction_id: UUID):
        try:
            return await self.post_interaction_store.get_by_id(post_interaction_id)
        except Exception as e:
            raise e

    async def like(self, post_id: UUID, user_id: UUID):
        try:
            return await self.post_interaction_store.update_like(post_id, user_id, True)
        except Exception as e:
            raise e

    async def unlike(self, post_id: UUID, user_id: UUID):
        try:
            return await self.post_interaction_store.update_like(post_id, user_id, False)
        except Exception as e:
            raise e
