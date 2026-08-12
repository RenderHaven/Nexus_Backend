from uuid import UUID
from app.domains.comment.repository import CommentRepository

class CommentService:
    def __init__(self, db):
        self.db = db
        self.comment_store = CommentRepository(db)

    async def get_comments_by_post_id(self, post_id: UUID):
        return await self.comment_store.get_by_post_id(post_id)

    async def get_replies_by_parent_id(self, post_interaction_id: UUID):
        return await self.comment_store.get_replies_by_parent_id(post_interaction_id)

    async def comment(self, post_id: UUID, user_id: UUID, comment: str):
        return await self.comment_store.add_comment(post_id, user_id, comment)

    async def add_comment_reply(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        return await self.comment_store.add_comment_reply(user_id, post_interaction_id, comment)

    async def edit_comment(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        return await self.comment_store.edit_comment(user_id, post_interaction_id, comment)

    async def delete(self, user_id: UUID, comment_id: UUID):
        # The old service did post_interaction_svc.delete(current_user.id, comment_id)
        # but the repository's delete method only takes one argument.
        # So we just pass it to comment_store.delete. We should check ownership if needed,
        # but keeping behavior same as previous interaction repo which ignored user_id in delete.
        return await self.comment_store.delete(comment_id)
