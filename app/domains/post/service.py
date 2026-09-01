from uuid import UUID

from fastapi import HTTPException

from app.db.models import ModerationStatus, PostStatus
from app.domains.post.rules import apply_is_active
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

    @staticmethod
    def _is_visible_to(post: Post, user_id: UUID | None) -> bool:
        """A hidden post (pending, held, archived, deleted) is only readable
        by its author. is_active is the single public-visibility flag."""
        return post.is_active or (user_id is not None and post.user_id == user_id)

    async def get_post(
        self,
        post_id: UUID,
        user_id: UUID | None = None,
        include_hidden: bool = False,
    ):
        post = await self.post_store.get(post_id)
        if not post:
            return None
        if not include_hidden and not self._is_visible_to(post, user_id):
            return None
        return await self._get_user_interactions(user_id, post)

    async def get_posts(
        self,
        post_ids: list[UUID],
        user_id: UUID | None = None,
        include_hidden: bool = False,
    ):
        posts = await self.post_store.get_many(post_ids)
        if not posts:
            return []
        if not include_hidden:
            posts = [p for p in posts if self._is_visible_to(p, user_id)]
            if not posts:
                return []
        return await self._get_user_interactions(user_id, posts)

    async def update_like_count(self, post_id: UUID, change: int):
        return await self.post_store.update_like_count(post_id, change)

    async def update_comment_count(self, post_id: UUID, change: int):
        return await self.post_store.update_comment_count(post_id, change)

    async def validate_references(self, post) -> None:
        """
        Check the rows a post points at before inserting it, so a bad id comes
        back as a clear 4xx instead of a foreign key violation.
        """
        repo = self.post_store.post_repo

        if not await repo.category_exists(post.category_id):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "category_not_found",
                    "message": "That category does not exist",
                },
            )

        if post.restricted_to_college_id is not None:
            if not await repo.college_exists(post.restricted_to_college_id):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "college_not_found",
                        "message": "The college you restricted this post to does not exist",
                    },
                )

    async def require_post(self, post_id: UUID) -> None:
        """Raise 404 rather than let a missing post surface as a DB error."""
        if not await self.post_store.post_repo.exists(post_id):
            raise HTTPException(
                status_code=404,
                detail={"code": "post_not_found", "message": "Post not found"},
            )

    async def add_post(self, post:Post):
        await self.validate_references(post)

        added_post_id = await self.post_store.add_post(post)
        if post.type == "collaboration" and added_post_id:
            from app.domains.chats.service import ChatService
            chat_service = ChatService(self.db)
            await chat_service.create_chat_room(added_post_id, post.user_id,name=post.title)
        return added_post_id

    # ------------------------------------------------------------------
    # Owner scoped writes
    #
    # These hit the repository directly instead of the pools: an author must
    # be able to see and act on posts that are not publicly visible yet.
    # ------------------------------------------------------------------

    async def _get_owned_post(self, post_id: UUID, user_id: UUID):
        db_post = await self.post_store.post_repo.get_for_update(post_id)

        if not db_post or db_post.status == PostStatus.deleted:
            raise HTTPException(status_code=404, detail="Post not found")

        if db_post.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Post is not owned by the user",
            )

        return db_post

    async def list_my_inactive_posts(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        """
        The author's posts that are not publicly visible: awaiting review,
        held, or archived.

        The visible half is served by the user post pool
        (GET /users/my_post_items), so the two listings never overlap.
        """
        db_posts = await self.post_store.post_repo.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            is_active=False,
        )
        return [Post.model_validate(p) for p in db_posts]

    async def _set_owner_status(
        self,
        post_id: UUID,
        user_id: UUID,
        status: PostStatus,
    ) -> UUID:
        """
        Check ownership, write the new status, drop the cached copy, and hand
        back the id so the caller can re-read the post if it needs to.
        """
        await self._get_owned_post(post_id, user_id)

        updated_id = await self.post_store.post_repo.set_status(post_id, status)
        await self.post_store.redis_store.delete(str(post_id))

        return updated_id

    async def archive_post(self, post_id: UUID, user_id: UUID) -> UUID:
        return await self._set_owner_status(
            post_id, user_id, PostStatus.archived
        )

    async def publish_post(self, post_id: UUID, user_id: UUID) -> UUID:
        return await self._set_owner_status(
            post_id, user_id, PostStatus.published
        )

    async def delete_post(self, post_id: UUID, user_id: UUID) -> UUID:
        """Soft delete. Permanent removal is a moderator action."""
        return await self._set_owner_status(
            post_id, user_id, PostStatus.deleted
        )

    async def update_post(self, post_id: UUID, user_id: UUID, payload) -> UUID:
        """
        Owner edit. Not wired to an endpoint yet.

        An edit invalidates the previous review, so the post goes back to the
        moderation queue and out of the pools until it is approved again.
        """
        db_post = await self._get_owned_post(post_id, user_id)

        editable = (
            "title",
            "content",
            "category_id",
            "type",
            "date_at",
            "restricted_to_college_id",
            "action_status",
        )

        for field in editable:
            value = getattr(payload, field, None)
            if value is not None:
                setattr(db_post, field, value)

        if getattr(payload, "resources", None) is not None:
            db_post.resources = [
                res.model_dump(mode="json") for res in payload.resources
            ]

        db_post.moderation_status = ModerationStatus.pending
        db_post.reviewed_by = None
        db_post.reviewed_at = None
        apply_is_active(db_post)

        await self.post_store.post_repo.update(db_post)
        await self.post_store.redis_store.delete(str(post_id))

        return post_id