from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model import PostComment, CommentEditLog, Post


class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, comment_id: UUID) -> PostComment | None:
        result = await self.db.execute(
            select(PostComment).where(PostComment.id == comment_id)
        )
        return result.scalar_one_or_none()

    async def add_comment(self, post_id: UUID, user_id: UUID, comment: str) -> PostComment:
        post_comment = PostComment(
            post_id=post_id,
            user_id=user_id,
            body=comment,
            is_active=True
        )
        self.db.add(post_comment)
        await self.db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(comment_count=Post.comment_count + 1)
        )
        await self.db.commit()
        await self.db.refresh(post_comment)
        return post_comment

    async def add_comment_reply(self, user_id: UUID, comment_id: UUID, comment: str) -> PostComment:
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
            is_active=True
        )
        self.db.add(reply_comment)
        await self.db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(comment_count=Post.comment_count + 1)
        )
        await self.db.commit()
        await self.db.refresh(reply_comment)
        return reply_comment

    async def edit_comment(self, user_id: UUID, comment_id: UUID, comment: str) -> PostComment:
        post_comment = await self.get_by_id(comment_id)
        if not post_comment:
            raise Exception("Comment not found")
        if not post_comment.user_id == user_id:
            raise Exception("Comment is not owned by the user")
        if not post_comment.is_active:
            raise Exception("Comment is not active")

        # Record edit log
        edit_log = CommentEditLog(
            comment_id=comment_id,
            previous_body=post_comment.body,
        )
        self.db.add(edit_log)

        post_comment.body = comment
        post_comment.is_edited = True
        self.db.add(post_comment)
        await self.db.commit()
        await self.db.refresh(post_comment)
        return post_comment

    async def delete(self, comment_id: UUID) -> bool:
        post_comment = await self.get_by_id(comment_id)
        if post_comment and post_comment.is_active:
            post_comment.is_active = False
            self.db.add(post_comment)
            await self.db.execute(
                update(Post)
                .where(Post.id == post_comment.post_id)
                .values(comment_count=func.greatest(0, Post.comment_count - 1))
            )
            await self.db.commit()
            return True
        return False

    async def get_by_post_id(self, post_id: UUID) -> list[PostComment]:
        result = await self.db.execute(
            select(PostComment)
            .where(PostComment.post_id == post_id)
            .where(PostComment.is_active == True)
        )
        return list(result.scalars().all())

    async def get_replies_by_parent_id(self, comment_id: UUID) -> list[PostComment]:
        result = await self.db.execute(
            select(PostComment)
            .where(PostComment.parent_id == comment_id)
            .where(PostComment.is_active == True)
        )
        return list(result.scalars().all())
