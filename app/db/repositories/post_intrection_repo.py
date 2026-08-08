from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model import PostInteraction,InteractionType


class PostInteractionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, post_interaction_id: UUID) -> PostInteraction | None:
        post_interaction = await self.db.get(PostInteraction, post_interaction_id)
        return post_interaction        
    
    async def create(self, post_interaction:PostInteraction)->PostInteraction:
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction
    
    async def update_like(self,post_id:UUID,user_id:UUID,like:bool):
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.post_id == post_id)
            .where(PostInteraction.user_id == user_id)
            .where(PostInteraction.type == InteractionType.like)
        )
        post_interaction = result.first()
        if post_interaction:
            if like and not post_interaction.is_active:
                post_interaction.is_active = True
                self.db.add(post_interaction)
                await self.db.commit()
                await self.db.refresh(post_interaction)
                return post_interaction
            elif not like and post_interaction.is_active:
                post_interaction.is_active = False
                self.db.add(post_interaction)
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
            await self.db.commit()
            await self.db.refresh(post_interaction)
            return post_interaction
    
    async def add_comment(self,post_id:UUID,user_id:UUID,comment:str):
        post_interaction = PostInteraction(
            post_id=post_id,
            user_id=user_id,
            type=InteractionType.comment,
            body=comment,
            is_active=True
        )
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction
    
    async def add_comment_reply(self,user_id:UUID,post_interaction_id:UUID,comment:str):
        parent_post_interaction = await self.get_by_id(post_interaction_id)
        if not parent_post_interaction:
            raise Exception("Parent post interaction not found")
        post_id = parent_post_interaction.post_id
        if not parent_post_interaction.type == InteractionType.comment:
            raise Exception("Parent post interaction is not a comment")
        if not parent_post_interaction.is_active:
            raise Exception("Parent post interaction is not active")

        post_interaction = PostInteraction(
            post_id=post_id,
            user_id=user_id,
            body=comment,
            parent_id=post_interaction_id,    
            is_active=True
        )
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction
    
    async def edit_comment(self,user_id:UUID,post_interaction_id:UUID,comment:str):
        post_interaction = await self.get_by_id(post_interaction_id)
        if not post_interaction:
            raise Exception("Post interaction not found")
        if not post_interaction.type == InteractionType.comment:
            raise Exception("Post interaction is not a comment")
        if not post_interaction.user_id == user_id:
            raise Exception("Post interaction is not owned by the user")
        if not post_interaction.is_active:
            raise Exception("Post interaction is not active")
        await self.delete(post_interaction_id)
        new_post_interaction = self.add_comment(post_interaction.post_id,post_interaction.user_id,comment)
        return new_post_interaction
    
    async def delete(self, post_interaction_id:UUID)->bool:
        await self.db.execute(
            update(PostInteraction)
            .where(PostInteraction.id == post_interaction_id)
            .values(
                is_active=False
            )
        )   
        await self.db.commit()
        return True
    
    async def get_by_post_id(self, post_id: UUID) -> list[PostInteraction]:
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.post_id == post_id)
        )
        return result.scalars().all()
    
    async def get_replies_by_parent_id(self, post_interaction_id: UUID) -> list[PostInteraction]:
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.parent_id == post_interaction_id)
        )
        return result.scalars().all()
    