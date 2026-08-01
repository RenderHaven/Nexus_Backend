from uuid import UUID
from app.redis.post_store import PostStore
from app.db.repositories.post_repo import PostRepository
from app.serializers.post_serializer import PostSerializer

class PostService:

    def __init__(self,db):
        self.post_store = PostStore()
        self.post_repo = PostRepository(db)
        self.db=db

    async def get_post(self, post_id):
        try:
            post = await self.post_store.get(post_id)
            if post:
                return post
            db_post = await self.post_repo.get_by_id(post_id)
            if db_post:
                post = PostSerializer.to_dict(db_post)
                await self.post_store.set(post_id, post)
            return post
        except Exception as e:
            raise e
    
    async def get_posts_by_engagement(self, limit: int):
        try:
            posts = await self.post_repo.list_all_posts(limit=limit)
            # posts.sort(key=lambda x: x.engagement_score, reverse=True)
            if posts:
                posts = [PostSerializer.to_dict(post) for post in posts]
                return posts
        except Exception as e:
            raise e
            
    async def get_posts(self, post_ids: list[UUID]):
        try:
            posts = await self.post_store.get_many(post_ids)
            if posts:
                return posts
            db_posts = await self.post_repo.posts_by_ids(post_ids)
            if db_posts:
                posts = [PostSerializer.to_dict(post) for post in db_posts]
                await self.post_store.set_many(post_ids, posts)
            return posts
        except Exception as e:
            raise e

    async def update_post(self, post):
        try:
            db_post = await self.post_repo.update(post)
            if db_post:
                updated_post = PostSerializer.to_dict(db_post)
                await self.post_store.set(post.id, updated_post)
            return updated_post
        except Exception as e:
            raise e

    async def delete_post(self, post_id):
        pass