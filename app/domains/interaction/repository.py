from uuid import UUID
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import PostReaction, Post, ReactionType


class PostInteractionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, post_reaction_id: UUID) -> PostReaction | None:
        result = await self.db.execute(
            select(PostReaction).where(PostReaction.id == post_reaction_id)
        )
        return result.scalar_one_or_none()

    async def create(self, post_reaction: PostReaction) -> PostReaction:
        self.db.add(post_reaction)
        await self.db.commit()
        await self.db.refresh(post_reaction)
        return post_reaction

    async def update_like(
        self,
        post_id: UUID,
        user_id: UUID,
        like: bool,
        commit: bool = True,
        reaction_type: ReactionType = ReactionType.inspired,
    ) -> PostReaction | None:
        result = await self.db.execute(
            select(PostReaction)
            .where(PostReaction.post_id == post_id)
            .where(PostReaction.user_id == user_id)
        )
        reaction = result.scalars().first()

        if like:
            if not reaction:
                reaction = PostReaction(
                    post_id=post_id,
                    user_id=user_id,
                    type=reaction_type,
                )
                self.db.add(reaction)
                # Update like_count on post
                await self.db.execute(
                    update(Post)
                    .where(Post.id == post_id)
                    .values(like_count=Post.like_count + 1)
                )
                if commit:
                    await self.db.commit()
                    await self.db.refresh(reaction)
            return reaction
        else:
            if reaction:
                await self.db.delete(reaction)
                await self.db.execute(
                    update(Post)
                    .where(Post.id == post_id)
                    .values(like_count=func.greatest(0, Post.like_count - 1))
                )
                if commit:
                    await self.db.commit()
                return reaction
            return None

    async def delete(self, post_reaction_id: UUID) -> bool:
        result = await self.db.execute(
            select(PostReaction).where(PostReaction.id == post_reaction_id)
        )
        reaction = result.scalars().first()
        if reaction:
            post_id = reaction.post_id
            await self.db.delete(reaction)
            await self.db.execute(
                update(Post)
                .where(Post.id == post_id)
                .values(like_count=func.greatest(0, Post.like_count - 1))
            )
            await self.db.commit()
            return True
        return False
