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
        try:
            post = await self.post_store.get(post_id)
            if not post:
                return None

        
            post.is_liked = await self._get_interaction(post_id=post.id,user_id=user_id)
                
            return post
        except Exception as e:
            raise e

    
    async def get_posts(self, post_ids: list[UUID], user_id: UUID | None = None):
        try:
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
        except Exception as e:
            raise e

    async def update_like_count(self, post_id: UUID, change: int):
        return await self.post_store.update_like_count(post_id, change)

    async def update_comment_count(self, post_id: UUID, change: int):
        return await self.post_store.update_comment_count(post_id, change)

    async def add_post(self, post):
        try:
            added_post = await self.post_store.add_post(post)
            return added_post
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

    async def build_registry(self):
        from app.db.models import Post, PostStatus
        from sqlalchemy import select
        print("Starting Post Registry build...")
        result = await self.db.execute(
            select(Post.id)
            .where(Post.is_active == True)
            .where(Post.status == PostStatus.published)
        )
        post_ids = [str(row[0]) for row in result.fetchall()]
        await self.post_store.post_store.rebuild_registry(post_ids)
        print(f"Post Registry build completed. {len(post_ids)} active posts.")

class PostUploadService:
    def __init__(self, db=None):
        self.db = db
        from app.domains.post.redis import PostStore
        self.post_store = PostStore()

    async def mark_uploading(self, post_id: UUID):
        await self.post_store.add_uploading_post(str(post_id))

    async def mark_completed(self, post_id: UUID):
        await self.post_store.remove_uploading_post(str(post_id))

    async def get_upload_status(self, post_id: UUID) -> dict:
        is_uploading = await self.post_store.is_uploading_post(str(post_id))
        if is_uploading:
            return {"post_id": str(post_id), "status": "uploading"}
        return {"post_id": str(post_id), "status": "completed"}