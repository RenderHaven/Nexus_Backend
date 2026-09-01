from datetime import datetime
from uuid import UUID
from fastapi import HTTPException

from app.domains.comments.schemas import Comment
from app.domains.comments.redis import CommentsRedis
from app.domains.comments.repository import CommentRepository


class CommentStorage:
    def __init__(self, db):
        self.redis_store = CommentsRedis()
        self.repo = CommentRepository(db)

    async def get_comment(self, comment_id: UUID) -> Comment | None:
        cached = await self.redis_store.get_comment(comment_id)
        if cached:
            return Comment.model_validate(cached)

        db_comment = await self.repo.get_by_id(comment_id)
        if not db_comment or not db_comment.is_active:
            return None

        comment = Comment.model_validate(db_comment)
        await self.redis_store.set_comment(comment.model_dump(mode="json"))
        return comment

    async def get_many_comments(self, comment_ids: list[UUID]) -> list[Comment]:
        if not comment_ids:
            return []

        # Fetch batch of comment bodies directly from Redis
        cached_items = await self.redis_store.get_many_comments(comment_ids)

        comment_map: dict[UUID, dict] = {}
        missing_ids: list[UUID] = []

        for cid, item in zip(comment_ids, cached_items):
            if item is not None:
                comment_map[cid] = item
            else:
                missing_ids.append(cid)

        # If any comments were missing from Redis, fetch them from DB repository
        if missing_ids:
            db_comments = await self.repo.get_by_ids(missing_ids)
            new_cache_items = []
            for db_c in db_comments:
                c_model = Comment.model_validate(db_c)
                c_dict = c_model.model_dump(mode="json")
                comment_map[db_c.id] = c_dict
                new_cache_items.append(c_dict)

            # Write missing comment bodies into Redis cache
            if new_cache_items:
                await self.redis_store.set_many_comments(new_cache_items)

        # Construct and return Comment models matching input ID order
        results = []
        for cid in comment_ids:
            if cid in comment_map:
                results.append(Comment.model_validate(comment_map[cid]))

        return results

    async def get_comment_ids(
        self,
        post_id: UUID,
        offset: tuple[UUID, datetime] | None = None,
        limit: int = 20,
    ) -> list[UUID]:
        """
        Root comment ids, newest first.

        Served straight from the database: the query is covered by
        idx_comments_post_root_cursor, and caching the list keyed only by post
        meant whichever caller asked first fixed the page size for everyone.
        """
        return await self.repo.get_by_post_id(
            post_id=post_id,
            offset=offset,
            limit=limit,
        )

    async def get_reply_ids(
        self,
        comment_id: UUID,
        offset: tuple[UUID, datetime] | None = None,
        limit: int = 20,
    ) -> list[UUID]:
        """Reply ids for one comment, newest first. See get_comment_ids."""
        return await self.repo.get_replies_by_parent_id(
            comment_id=comment_id,
            offset=offset,
            limit=limit,
        )

    async def add_comment(self, post_id: UUID, user_id: UUID, body: str, comment_id: UUID) -> Comment:
        db_comment = await self.repo.add_comment(post_id, user_id, body, comment_id)
        comment = Comment.model_validate(db_comment)
        await self.redis_store.set_comment(comment.model_dump(mode="json"))
        return comment

    async def add_comment_reply(self, user_id: UUID, comment_id: UUID, body: str, reply_id: UUID) -> Comment:
        db_reply = await self.repo.add_comment_reply(user_id, comment_id, body, reply_id)
        reply = Comment.model_validate(db_reply)
        await self.redis_store.set_comment(reply.model_dump(mode="json"))
        parent_comment = await self.get_comment(comment_id)
        if parent_comment:
            parent_comment.reply_count += 1
            await self.redis_store.set_comment(parent_comment.model_dump(mode="json"))
        return reply

    async def edit_comment(self, user_id: UUID, comment_id: UUID, body: str) -> Comment:
        db_comment = await self.repo.edit_comment(user_id, comment_id, body)
        comment = Comment.model_validate(db_comment)
        await self.redis_store.set_comment(comment.model_dump(mode="json"))
        return comment

    async def delete_comment(
        self,
        user_id: UUID,
        comment_id: UUID,
    ) -> tuple[bool, UUID | None, int]:
        """
        Delete a comment the user owns, along with its replies.

        Returns whether it happened, the post it belonged to, and how many
        comments in total were removed.
        """
        comment = await self.get_comment(comment_id)

        if not comment:
            raise HTTPException(
                status_code=404,
                detail={"code": "comment_not_found", "message": "Comment not found"},
            )

        if comment.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "not_comment_author",
                    "message": "Comment is not owned by the user",
                },
            )

        success, removed_ids = await self.repo.delete(comment_id)

        if not success:
            return False, None, 0

        for removed_id in removed_ids:
            await self.redis_store.delete_comment(removed_id)

        if comment.parent_id:
            parent_comment = await self.get_comment(comment.parent_id)
            if parent_comment:
                parent_comment.reply_count = max(0, parent_comment.reply_count - 1)
                await self.redis_store.set_comment(
                    parent_comment.model_dump(mode="json")
                )

        return True, comment.post_id, len(removed_ids)
