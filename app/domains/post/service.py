from uuid import UUID
from app.domains.post.storage import PostStorage

class PostService:

    def __init__(self,db):
        self.db=db
        self.post_store = PostStorage(db)

    async def _get_interaction(self, post_id: UUID, user_id: UUID | None = None):
        if not user_id:
            return False
        
        from app.domains.reaction.storage import ReactionStorage
        reaction_store = ReactionStorage(self.db)
        
        is_liked = await reaction_store.is_liked(post_id=post_id, user_id=user_id)
        return is_liked

    async def get_post(self, post_id: UUID, user_id: UUID | None = None):
        post = await self.post_store.get(post_id)
        if not post:
            return None
        post.is_liked = await self._get_interaction(post_id=post.id,user_id=user_id)
            
        return post

    async def get_posts(self, post_ids: list[UUID], user_id: UUID | None = None):
        posts = await self.post_store.get_many(post_ids)
        if not posts:
            return []
            
        from app.domains.reaction.storage import ReactionStorage
        reaction_store = ReactionStorage(self.db)
        
        p_ids = [str(post.id) for post in posts]
        
        likes = {}
        if user_id:
            likes = await reaction_store.are_liked(p_ids, user_id)
                
        for post in posts:
            if user_id:
                post.is_liked = likes.get(str(post.id), False)
                
        return posts

    async def update_like_count(self, post_id: UUID, change: int):
        return await self.post_store.update_like_count(post_id, change)

    async def update_comment_count(self, post_id: UUID, change: int):
        return await self.post_store.update_comment_count(post_id, change)

    async def add_post(self, post):
        added_post = await self.post_store.add_post(post)
        return added_post

    async def update_post(self, post):
        updated_post = await self.post_store.update(post)
        return updated_post

    async def delete_post(self, post_id):
        is_deleted = await self.post_store.delete(post_id)
        return is_deleted
