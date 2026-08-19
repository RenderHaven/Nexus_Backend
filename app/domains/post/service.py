from uuid import UUID
from app.domains.post.storage import PostStorage

class PostService:

    def __init__(self,db):
        self.db=db
        self.post_store = PostStorage(db)

        
    async def get_post(self, post_id: UUID, user_id: UUID | None = None):
        try:
            post = await self.post_store.get(post_id)
            if not post:
                return None
                
            from app.domains.interaction.storage import InteractionStorage
            interaction_store = InteractionStorage(self.db)
            
            post.like_count = await interaction_store.get_likes_count(post.id)
            if user_id:
                post.is_liked = await interaction_store.is_liked(post.id, user_id)
                
            return post
        except Exception as e:
            raise e

    
    async def get_posts(self, post_ids: list[UUID], user_id: UUID | None = None):
        try:
            posts = await self.post_store.get_many(post_ids)
            if not posts:
                return []
                
            from app.domains.interaction.storage import InteractionStorage
            interaction_store = InteractionStorage(self.db)
            
            p_ids = [str(post.id) for post in posts]
            counts = await interaction_store.get_likes_counts(p_ids)
            
            likes = {}
            if user_id:
                likes = await interaction_store.are_liked(p_ids, user_id)
                
            for post in posts:
                post.like_count = counts.get(str(post.id), 0)
                if user_id:
                    post.is_liked = likes.get(str(post.id), False)
                    
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

    async def build_registry(self):
        from app.db.model import Post, PostStatus
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