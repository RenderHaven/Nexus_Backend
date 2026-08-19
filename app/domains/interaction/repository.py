from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model import PostInteraction, InteractionType

class PostInteractionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, post_interaction_id: UUID) -> PostInteraction | None:
        post_interaction = await self.db.get(PostInteraction, post_interaction_id)
        return post_interaction

    async def create(self, post_interaction: PostInteraction) -> PostInteraction:
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction

    async def update_like(self, post_id: UUID, user_id: UUID, like: bool, commit: bool = True):
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.post_id == post_id)
            .where(PostInteraction.user_id == user_id)
            .where(PostInteraction.type == InteractionType.like)
        )
        post_interaction = result.first()
        if post_interaction:
            if type(post_interaction) is tuple:
                post_interaction = post_interaction[0]
            if like and not post_interaction.is_active:
                post_interaction.is_active = True
                self.db.add(post_interaction)
                if commit:
                    await self.db.commit()
                    await self.db.refresh(post_interaction)
                return post_interaction
            elif not like and post_interaction.is_active:
                post_interaction.is_active = False
                self.db.add(post_interaction)
                if commit:
                    await self.db.commit()
                    await self.db.refresh(post_interaction)
                return post_interaction
            else:
                return post_interaction
        else:
            post_interaction = PostInteraction(
                post_id=post_id,
                user_id=user_id,
                type=InteractionType.like,
                is_active=like
            )
            self.db.add(post_interaction)
            if commit:
                await self.db.commit()
                await self.db.refresh(post_interaction)
            return post_interaction

    async def delete(self, post_interaction_id: UUID) -> bool:
        await self.db.execute(
            update(PostInteraction)
            .where(PostInteraction.id == post_interaction_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return True
