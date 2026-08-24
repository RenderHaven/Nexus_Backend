from datetime import datetime
from uuid import UUID
from app.domains.comments.domain import Comment
from app.domains.comments.storage import CommentStorage
from app.domains.cursor.service import CursorService
from app.kafka.client import kafka_manager
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

    async def comment(self, post_id: UUID, user_id: UUID, comment: str) -> Comment:
        result = await self.comment_store.add_comment(post_id, user_id, comment)
        await kafka_manager.send_event(
            settings.KAFKA_COMMENTS_TOPIC,
            {
                "action": "comment_added",
                "post_id": str(post_id),
                "user_id": str(user_id),
                "comment_id": str(result.id),
            },
        )
        return result

    async def add_comment_reply(self, user_id: UUID, comment_id: UUID, comment: str) -> Comment:
        result = await self.comment_store.add_comment_reply(user_id, comment_id, comment)
        await kafka_manager.send_event(
            settings.KAFKA_COMMENTS_TOPIC,
            {
                "action": "reply_added",
                "parent_id": str(comment_id),
                "user_id": str(user_id),
                "comment_id": str(result.id),
            },
        )
        return result

    async def edit_comment(self, user_id: UUID, comment_id: UUID, comment: str) -> Comment:
        result = await self.comment_store.edit_comment(user_id, comment_id, comment)
        await kafka_manager.send_event(
            settings.KAFKA_COMMENTS_TOPIC,
            {
                "action": "comment_edited",
                "comment_id": str(comment_id),
                "user_id": str(user_id),
            },
        )
        return result

    async def delete(self, user_id: UUID, comment_id: UUID) -> bool:
        result = await self.comment_store.delete_comment(user_id, comment_id)
        if result:
            await kafka_manager.send_event(
                settings.KAFKA_COMMENTS_TOPIC,
                {
                    "action": "comment_deleted",
                    "comment_id": str(comment_id),
                    "user_id": str(user_id),
                },
            )
        return result
