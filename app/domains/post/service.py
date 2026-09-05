from uuid import UUID

from fastapi import HTTPException

from app.db.models import ModerationStatus, PostStatus
from app.domains.post.rules import apply_is_active
from app.rules import Actor
from app.domains.post.storage import PostStorage
from app.domains.post.schemas import Post

class PostService:

    def __init__(self, db):
        self.db = db
        self.post_store = PostStorage(db)

    async def _get_user_interactions(
        self,
        actor: Actor,
        posts: Post | list[Post],
    ) -> Post | list[Post]:
        """
        Annotate one or many posts with user-specific interaction state
        (is_liked, collaboration status). Always batches Redis calls
        internally regardless of whether one post or many were passed.
        """
        is_single = isinstance(posts, Post)
        post_list = [posts] if is_single else posts

        user_id = actor.id

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
    def _is_visible_to(post: Post, actor: Actor) -> bool:
        """
        Who may read this post.

        is_active is the single public-visibility flag, and a public post is
        readable from any college -- including a post restricted to one
        college, which limits who may *join* the collaboration, not who may
        see it.

        A hidden post (pending, held, removed, archived) is readable by its
        author, by staff of that post's own college, and by an admin.
        """
        return (
            post.is_active
            or actor.owns(post)
            or actor.can_see_hidden(post.college_id)
        )

    async def get_post(self, post_id: UUID, actor: Actor | None = None):
        actor = actor or Actor()

        post = await self.post_store.get(post_id)

        if not post or not self._is_visible_to(post, actor):
            return None

        return await self._get_user_interactions(actor, post)

    async def get_posts(self, post_ids: list[UUID], actor: Actor | None = None):
        actor = actor or Actor()

        posts = await self.post_store.get_many(post_ids)

        if not posts:
            return []

        posts = [p for p in posts if self._is_visible_to(p, actor)]

        if not posts:
            return []

        return await self._get_user_interactions(actor, posts)

    async def _reindex(self, post_id: UUID) -> None:
        """
        Push a post's current state into the search index.

        Imported here rather than at module scope because the search service
        reads back through PostService to hydrate its results. Best effort by
        construction -- SearchService swallows and logs its own failures, so a
        search cluster being down can never fail a post write.
        """
        from app.domains.search.service import SearchService

        await SearchService(self.db).update_post_search(post_id)

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

        if added_post_id:
            await self._reindex(added_post_id)

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

    async def _get_owned_post(self, post_id: UUID, actor: Actor):
        """
        Strictly the author's own post.

        Staff are deliberately not let through here: a moderator acts on
        someone else's post through PostAdminService, which records the
        decision. Editing another person's post body is nobody's job.
        """
        db_post = await self.post_store.post_repo.get_for_update(post_id)

        if not db_post or db_post.status == PostStatus.deleted:
            raise HTTPException(
                status_code=404,
                detail={"code": "post_not_found", "message": "Post not found"},
            )

        if not actor.owns(db_post):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden",
                    "message": "Post is not owned by the user",
                },
            )

        return db_post

    async def list_my_inactive_posts(
        self,
        actor: Actor,
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
            user_id=actor.id,
            limit=limit,
            offset=offset,
            is_active=False,
        )
        return [Post.model_validate(p) for p in db_posts]

    async def _set_owner_status(
        self,
        post_id: UUID,
        actor: Actor,
        status: PostStatus,
    ) -> UUID:
        """
        Check ownership, write the new status, drop the cached copy, and hand
        back the id so the caller can re-read the post if it needs to.
        """
        await self._get_owned_post(post_id, actor)

        updated_id = await self.post_store.post_repo.set_status(post_id, status)
        await self.post_store.redis_store.delete(str(post_id))
        await self._reindex(post_id)

        return updated_id

    async def archive_post(self, post_id: UUID, actor: Actor) -> UUID:
        return await self._set_owner_status(
            post_id, actor, PostStatus.archived
        )

    async def publish_post(self, post_id: UUID, actor: Actor) -> UUID:
        return await self._set_owner_status(
            post_id, actor, PostStatus.published
        )

    async def delete_post(self, post_id: UUID, actor: Actor) -> UUID:
        """Soft delete. Permanent removal is a moderator action."""
        return await self._set_owner_status(
            post_id, actor, PostStatus.deleted
        )

    async def update_post(self, post_id: UUID, actor: Actor, payload) -> UUID:
        """
        Owner edit. Not wired to an endpoint yet.

        An edit invalidates the previous review, so the post goes back to the
        moderation queue and out of the pools until it is approved again.
        """
        db_post = await self._get_owned_post(post_id, actor)

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
        await self._reindex(post_id)

        return post_id