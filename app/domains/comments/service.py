from datetime import datetime
from uuid import UUID
from app.domains.comments.schemas import Comment
from app.domains.comments.storage import CommentStorage
from app.domains.cursor.service import CursorService

from app.config import settings


class CommentService:
    def __init__(self, db):
        self.db = db
        self.comment_store = CommentStorage(db)
        self.cursor_svc = CursorService()

    async def _get_offset(self, cursor: str | None = None) -> tuple[UUID, datetime] | None:
        if not cursor:
            return None
        cursor_data = await self.cursor_svc.get_cursor(cursor)
        if not cursor_data or "offset" not in cursor_data:
            return None
        offset = cursor_data["offset"]
        return (UUID(offset["id"]), datetime.fromisoformat(offset["created_at"]))

    async def get_comment(self, comment_id: UUID) -> Comment | None:
        return await self.comment_store.get_comment(comment_id)

    async def get_comment_ids(
        self,
        post_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[UUID], str | None]:
        offset = await self._get_offset(cursor)
        ids = await self.comment_store.get_comment_ids(
            post_id=post_id,
            offset=offset,
            limit=limit,
        )
        if not ids:
            return [], None

        last_comment = await self.get_comment(ids[-1])
        if not last_comment:
            return ids, None

        next_cursor = await self.cursor_svc.update_cursor(
            {"offset": {"id": str(last_comment.id), "created_at": last_comment.created_at.isoformat()}},
            cursor
        )
        return ids, next_cursor

    async def get_many_comments(self, comment_ids: list[UUID]) -> list[Comment]:
        return await self.comment_store.get_many_comments(comment_ids)

    async def get_reply_ids(
        self,
        comment_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[UUID], str | None]:
        offset = await self._get_offset(cursor)
        ids = await self.comment_store.get_reply_ids(
            comment_id=comment_id,
            offset=offset,
            limit=limit,
        )
        if not ids:
            return [], None

        last_comment = await self.get_comment(ids[-1])
        if not last_comment:
            return ids, None

        next_cursor = await self.cursor_svc.update_cursor(
            {"offset": {"id": str(last_comment.id), "created_at": last_comment.created_at.isoformat()}},
            cursor
        )
        return ids, next_cursor

    async def comment(self, post_id: UUID, user_id: UUID, comment: str) -> dict:
        import uuid

        from app.domains.post.service import PostService

        post_svc = PostService(self.db)
        await post_svc.require_post(post_id)

        comment_id = uuid.uuid4()
        
        created_comment = await self.comment_store.add_comment(
            post_id=post_id,
            user_id=user_id,
            body=comment,
            comment_id=comment_id
        )

        from app.domains.post.service import PostService
        post_svc = PostService(self.db)
        await post_svc.post_store.update_comment_count(post_id, 1)

        return {
            "status": "success",
            "action": "comment_added",
            "comment_id": str(comment_id)
        }

    async def add_comment_reply(self, user_id: UUID, comment_id: UUID, comment: str) -> dict:
        import uuid
        reply_id = uuid.uuid4()
        
        reply = await self.comment_store.add_comment_reply(
            user_id=user_id,
            comment_id=comment_id,
            body=comment,
            reply_id=reply_id
        )

        if reply and reply.post_id:
            from app.domains.post.service import PostService
            post_svc = PostService(self.db)
            await post_svc.post_store.update_comment_count(reply.post_id, 1)

        return {
            "status": "success",
            "action": "reply_added",
            "comment_id": str(reply_id)
        }

    async def edit_comment(self, user_id: UUID, comment_id: UUID, comment: str) -> dict:
        edited_comment = await self.comment_store.edit_comment(
            user_id=user_id,
            comment_id=comment_id,
            body=comment
        )
        return {
            "status": "success",
            "action": "comment_edited",
            "comment_id": str(comment_id)
        }

    async def delete(self, user_id: UUID, comment_id: UUID) -> dict:
        success, post_id, removed = await self.comment_store.delete_comment(
            user_id, comment_id
        )

        # A comment takes its replies with it, so the post loses all of them.
        if success and post_id and removed:
            from app.domains.post.service import PostService
            post_svc = PostService(self.db)
            await post_svc.post_store.update_comment_count(post_id, -removed)

        return {
            "status": "success" if success else "failed",
            "action": "comment_deleted",
            "comment_id": str(comment_id),
            "removed_count": removed,
        }

    async def process_batch(self, batch_messages):
        """Process a batch of comment events (DB + Redis update)."""
        count = 0
        from collections import defaultdict
        net_comments = defaultdict(int)

        for tp, messages in batch_messages.items():
            for msg in messages:
                data = msg.value
                action = data.get("action")
                user_id = UUID(data.get("user_id"))

                if action == "comment_added":
                    post_id_str = data.get("post_id")
                    post_id = UUID(post_id_str)
                    comment_id = UUID(data.get("comment_id"))
                    comment = data.get("comment")
                    await self.comment_store.add_comment(post_id, user_id, comment, comment_id)
                    net_comments[post_id_str] += 1
                elif action == "reply_added":
                    parent_id = UUID(data.get("parent_id"))
                    comment_id = UUID(data.get("comment_id"))
                    comment = data.get("comment")
                    reply = await self.comment_store.add_comment_reply(user_id, parent_id, comment, comment_id)
                    net_comments[str(reply.post_id)] += 1
                elif action == "comment_edited":
                    comment_id = UUID(data.get("comment_id"))
                    comment = data.get("comment")
                    await self.comment_store.edit_comment(user_id, comment_id, comment)
                elif action == "comment_deleted":
                    comment_id = UUID(data.get("comment_id"))
                    success, post_id, removed = await self.comment_store.delete_comment(
                        user_id, comment_id
                    )
                    if success and post_id:
                        net_comments[str(post_id)] -= removed
                count += 1
        
        if net_comments:
            from app.domains.post.service import PostService
            post_svc = PostService(self.db)
            for post_id_str, change in net_comments.items():
                if change != 0:
                    await post_svc.post_store.update_comment_count(UUID(post_id_str), change)
                    
        return count
