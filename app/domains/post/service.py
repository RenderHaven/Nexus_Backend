from uuid import UUID
from app.domains.post.storage import PostStorage

class PostService:

    def __init__(self,db):
        self.db=db
        self.post_store = PostStorage(db)
        
    async def get_post(self, post_id:UUID):
        try:
            post = await self.post_store.get(post_id)
            return post
        except Exception as e:
            raise e
    
    async def get_posts(self, post_ids: list[UUID]):
        try:
            posts = await self.post_store.get_many(post_ids)
            return posts
        except Exception as e:
            raise e

    async def update_post(self, post):
        try:
            updated_post = await self.post_store.update(post)
            return updated_post
        except Exception as e:
            raise e

    async def delete_post(self, post_id):
        try:
            is_deleted = await self.post_store.delete(post_id)
            return is_deleted
        except Exception as e:
            raise e