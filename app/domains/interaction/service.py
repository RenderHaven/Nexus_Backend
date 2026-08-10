from sqlalchemy import UUID
from app.db.repositories.post_intrection_repo import PostInteractionRepository

class PostInteractionsService: 

    def __init__(self,db):
        self.db=db
        self.post_interaction_store = PostInteractionRepository(db)
        
    async def get_post_interaction(self, post_interaction_id:UUID):
        try:
            post_interaction = await self.post_interaction_store.get_by_id(post_interaction_id)
            return post_interaction
        except Exception as e:
            raise e

    async def get_comments_by_post_id(self,post_id:UUID):
        try:
            post_interaction = await self.post_interaction_store.get_by_post_id(post_id)
            return post_interaction
        except Exception as e:
            raise e
    async def get_replies_by_parent_id(self,post_interaction_id:UUID):
        try:
            post_interaction = await self.post_interaction_store.get_replies_by_parent_id(post_interaction_id)
            return post_interaction
        except Exception as e:
            raise e
            
    async def like(self,post_id:UUID,user_id:UUID):
        try:
            post_interaction = await self.post_interaction_store.update_like(post_id,user_id,True)
            return post_interaction
        except Exception as e:
            raise e
    
    async def unlike(self,post_id:UUID,user_id:UUID):
        try:
            post_interaction = await self.post_interaction_store.update_like(post_id,user_id,False)
            return post_interaction
        except Exception as e:
            raise e

    async def comment(self,post_id:UUID,user_id:UUID,comment:str):
        try:
            post_interaction = await self.post_interaction_store.add_comment(post_id,user_id,comment)
            return post_interaction
        except Exception as e:
            raise e
    
    async def add_comment_reply(self,user_id:UUID,post_interaction_id:UUID,comment:str):
        try:
            post_interaction = await self.post_interaction_store.add_comment_reply(user_id,post_interaction_id,comment)
            return post_interaction
        except Exception as e:
            raise e
    
    async def edit_comment(self,user_id:UUID,post_interaction_id:UUID,comment:str):
        try:
            post_interaction = await self.post_interaction_store.edit_comment(user_id,post_interaction_id,comment)
            return post_interaction
        except Exception as e:
            raise e