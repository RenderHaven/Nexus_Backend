from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PostComment, CommentEditLog, Post


class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        comment_id: UUID,
    ) -> PostComment | None:
        result = await self.db.execute(
            select(PostComment).where(
                PostComment.id == comment_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_ids(
        self,
        comment_ids: list[UUID],
    ) -> list[PostComment]:
        if not comment_ids:
            return []
        result = await self.db.execute(
            select(PostComment).where(
                PostComment.id.in_(comment_ids),
                PostComment.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    # =========================
    # Create
    # =========================

    async def add_comment(
        self,
        post_id: UUID,
        user_id: UUID,
        comment: str,
    ) -> PostComment:
        post_comment = PostComment(
            post_id=post_id,
            user_id=user_id,
            body=comment,
            is_active=True,
        )

        self.db.add(post_comment)

        await self.db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(
                comment_count=Post.comment_count + 1
            )
        )

        await self.db.commit()
        await self.db.refresh(post_comment)

        return post_comment

    async def add_comment_reply(
        self,
        user_id: UUID,
        comment_id: UUID,
        comment: str,
    ) -> PostComment:
        parent_comment = await self.get_by_id(comment_id)

        if not parent_comment:
            raise Exception("Parent comment not found")

        if not parent_comment.is_active:
            raise Exception("Parent comment is not active")

        post_id = parent_comment.post_id

        reply_comment = PostComment(
            post_id=post_id,
            user_id=user_id,
            body=comment,
            parent_id=comment_id,
            is_active=True,
        )

        self.db.add(reply_comment)

        # Increment post comment count
        await self.db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(
                comment_count=Post.comment_count + 1
            )
        )

        # Increment parent's reply count
        await self.db.execute(
            update(PostComment)
            .where(PostComment.id == comment_id)
            .values(
                reply_count=PostComment.reply_count + 1
            )
        )

        await self.db.commit()
        await self.db.refresh(reply_comment)

        return reply_comment

    # =========================
    # Update
    # =========================

    async def edit_comment(
        self,
        user_id: UUID,
        comment_id: UUID,
        comment: str,
    ) -> PostComment:
        post_comment = await self.get_by_id(comment_id)

        if not post_comment:
            raise Exception("Comment not found")

        if post_comment.user_id != user_id:
            raise Exception(
                "Comment is not owned by the user"
            )

        if not post_comment.is_active:
            raise Exception("Comment is not active")

        edit_log = CommentEditLog(
            comment_id=comment_id,
            previous_body=post_comment.body,
        )

        self.db.add(edit_log)

        post_comment.body = comment
        post_comment.is_edited = True

        await self.db.commit()
        await self.db.refresh(post_comment)

        return post_comment

    # =========================
    # Delete
    # =========================

    async def delete(
        self,
        comment_id: UUID,
    ) -> bool:
        post_comment = await self.get_by_id(comment_id)

        if not post_comment or not post_comment.is_active:
            return False

        post_comment.is_active = False

        # Decrease post comment count
        await self.db.execute(
            update(Post)
            .where(Post.id == post_comment.post_id)
            .values(
                comment_count=func.greatest(
                    0,
                    Post.comment_count - 1,
                )
            )
        )

        # If this is a reply, decrease parent's reply count
        if post_comment.parent_id is not None:
            await self.db.execute(
                update(PostComment)
                .where(
                    PostComment.id == post_comment.parent_id
                )
                .values(
                    reply_count=func.greatest(
                        0,
                        PostComment.reply_count - 1,
                    )
                )
            )

        await self.db.commit()

        return True

    # =========================
    # Fetch root comments
    # =========================

    async def get_by_post_id(
        self,
        post_id: UUID,
        offset: tuple[UUID, datetime] | None = None,
        limit: int = 20,
    ) -> list[UUID]:

        query = (
            select(PostComment.id)
            .where(
                PostComment.post_id == post_id,
                PostComment.parent_id.is_(None),
                PostComment.is_active.is_(True),
            )
            .order_by(
                PostComment.created_at.desc(),
                PostComment.id.desc(),
            )
            .limit(limit)
        )

        if offset is not None:
            cid, created_at = offset
            query = query.where(
                or_(
                    PostComment.created_at < created_at,
                    and_(
                        PostComment.created_at == created_at,
                        PostComment.id < cid,
                    ),
                )
            )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    # =========================
    # Fetch replies
    # =========================

    async def get_replies_by_parent_id(
        self,
        comment_id: UUID,
        offset: tuple[UUID, datetime] | None = None,
        limit: int = 20,
    ) -> list[UUID]:

        query = (
            select(PostComment.id)
            .where(
                PostComment.parent_id == comment_id,
                PostComment.is_active.is_(True),
            )
            .order_by(
                PostComment.created_at.desc(),
                PostComment.id.desc(),
            )
            .limit(limit)
        )

        if offset is not None:
            cid, created_at = offset
            query = query.where(
                or_(
                    PostComment.created_at < created_at,
                    and_(
                        PostComment.created_at == created_at,
                        PostComment.id < cid,
                    ),
                )
            )

        result = await self.db.execute(query)

        return list(result.scalars().all())