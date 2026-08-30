from uuid import UUID
from app.domains.post.storage import PostStorage
from app.domains.post.schemas import Post

class PostService:

    def __init__(self, db):
        self.db = db
        self.post_store = PostStorage(db)

    async def _get_user_interactions(
        self,
        user_id: UUID | None,
        posts: Post | list[Post],
    ) -> Post | list[Post]:
        """
        Annotate one or many posts with user-specific interaction state
        (is_liked, collaboration status). Always batches Redis calls
        internally regardless of whether one post or many were passed.
        """
        is_single = isinstance(posts, Post)
        post_list = [posts] if is_single else posts

        if not user_id or not post_list:
            return posts

        from app.domains.reaction.service import LikeService
        like_svc = LikeService(self.db)

        p_ids = [str(post.id) for post in post_list]
        likes = await like_svc.are_liked(p_ids, user_id)

        collab_ids = [str(post.id) for post in post_list if post.type == "collaboration"]
        collab_statuses = {}
        if collab_ids:
            from app.domains.collaboration.service import CollabStatusService
            collab_status_svc = CollabStatusService(self.db)
            collab_statuses = await collab_status_svc.get_statuses(collab_ids, user_id)

        for post in post_list:
            post.is_liked = likes.get(str(post.id), False)
            if post.type == "collaboration":
                post.collab_status = collab_statuses.get(str(post.id))

        return posts

    async def get_post(self, post_id: UUID, user_id: UUID | None = None):
        post = await self.post_store.get(post_id)
        if not post:
            return None
        return await self._get_user_interactions(user_id, post)

    async def get_posts(self, post_ids: list[UUID], user_id: UUID | None = None):
        posts = await self.post_store.get_many(post_ids)
        if not posts:
            return []
        return await self._get_user_interactions(user_id, posts)

    async def update_like_count(self, post_id: UUID, change: int):
        return await self.post_store.update_like_count(post_id, change)

    async def update_comment_count(self, post_id: UUID, change: int):
        return await self.post_store.update_comment_count(post_id, change)

    async def add_post(self, post):
        return await self.post_store.add_post(post)

    async def update_post(self, post):
        return await self.post_store.update(post)

    async def delete_post(self, post_id):
        return await self.post_store.delete(post_id)