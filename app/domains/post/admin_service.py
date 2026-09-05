from uuid import UUID

from fastapi import HTTPException

from app.db.models import ModerationStatus
from app.domains.logs import ModerationLogService
from app.domains.post.schemas import (
    BulkModerationFailure,
    BulkModerationResult,
    ModerationCounts,
    ModerationLogEntry,
    Post,
)
from app.domains.post.service import PostService
from app.domains.post.storage import PostStorage
from app.rules import Actor, Permission

# Re-exported so callers can keep importing these from the post domain, but
# the rules themselves live in app/rules.
from app.rules import RESTRICTED_POST_TYPES  # noqa: F401


def require_moderator(user):
    """
    Deprecated. Role-only check, with no college scope -- use
    actor.require(Permission.MODERATE_POST, college_id) instead so the
    caller's campus is checked too. Kept until the last import is gone.
    """
    from app.rules import require_permission

    return require_permission(user, Permission.MODERATE_POST)


class PostAdminService:
    """
    Privileged post operations: creating restricted post types, moving posts
    through moderation, and permanent deletion.

    Shares PostStorage with PostService so the Redis cache stays consistent,
    but every read/write here goes straight to the repository — moderators
    work on posts that are deliberately absent from the public pools.
    """

    def __init__(self, db):
        self.db = db
        self.post_store = PostStorage(db)
        self.post_repo = self.post_store.post_repo
        self.post_svc = PostService(db)
        self.logs = ModerationLogService(db)

    # ------------------------------------------------------------------
    # Search index
    # ------------------------------------------------------------------

    def _search(self):
        # Imported lazily: the search service reads back through the post
        # domain to hydrate its results.
        from app.domains.search.service import SearchService

        return SearchService(self.db)

    async def _reindex(self, post_id: UUID) -> None:
        """Best effort by construction -- SearchService logs and swallows its
        own failures, so moderation never breaks on a search outage."""
        await self._search().update_post_search(post_id)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def add_post(self, post) -> UUID:
        """
        Create a restricted post (event / opportunity). The caller is
        responsible for the role check; college_id comes from the creating
        moderator, exactly like an ordinary post.
        """
        await self.post_svc.validate_references(post)

        db_post = await self.post_repo.create(post)

        await self._reindex(db_post.id)

        await self.logs.log_restricted_create(
            post_id=db_post.id,
            moderator_id=post.user_id,
            post_type=getattr(post.type, "value", str(post.type)),
        )

        return db_post.id

    # ------------------------------------------------------------------
    # Moderation
    # ------------------------------------------------------------------

    async def list_moderation_queue(
        self,
        actor: Actor,
        moderation_status: ModerationStatus,
        filters,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        """
        One page of the review queue.

        The college on the filters is what the caller asked for; what the
        query actually uses is whatever scope_college returns. A moderator
        gets their own campus filled in when they ask for nothing, and a 403
        if they hand-edit the query string to name another.
        """
        college_id = actor.scope_college(filters.college_id)

        actor.require(Permission.MODERATE_POST, college_id)

        db_posts = await self.post_repo.list_by_moderation_status(
            moderation_status=moderation_status,
            limit=limit,
            offset=offset,
            college_id=college_id,
            user_id=filters.user_id,
            category_id=filters.category_id,
            post_type=filters.type,
            q=filters.q,
            date_from=filters.date_from,
            date_to=filters.date_to,
            sort=filters.sort.value,
            order=filters.order.value,
        )
        return await self.post_svc.hydrate_references(
            [Post.model_validate(p) for p in db_posts]
        )

    async def count_by_status(
        self,
        actor: Actor,
        college_id: UUID | None = None,
    ) -> ModerationCounts:
        """Per-status totals for the queue tab badges."""
        college_id = actor.scope_college(college_id)

        actor.require(Permission.MODERATE_POST, college_id)

        counts = await self.post_repo.counts_by_moderation_status(college_id)

        return ModerationCounts(
            **{
                status.value: counts.get(status, 0)
                for status in ModerationStatus
            }
        )

    async def update_moderation_status(
        self,
        post_id: UUID,
        moderation_status: ModerationStatus,
        reviewer_id: UUID,
        note: str | None = None,
        actor: Actor | None = None,
    ) -> UUID:
        """
        Approve, hold or remove one post.

        A decision is not final: staff may move a post between these states
        at any time, and each move is recorded as its own audit entry.
        """
        if actor is not None:
            post = await self.post_repo.get_for_update(post_id)

            if not post:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "post_not_found", "message": "Post not found"},
                )

            actor.require(Permission.MODERATE_POST, post.college_id)

        updated_id = await self.post_repo.set_moderation_status(
            post_id=post_id,
            moderation_status=moderation_status,
            reviewer_id=reviewer_id,
        )

        if not updated_id:
            raise HTTPException(status_code=404, detail="Post not found")

        # The cached copy still carries the old moderation state, so drop it
        # and let the next read rebuild it.
        await self.post_store.redis_store.delete(str(post_id))
        await self._reindex(post_id)

        await self.logs.log_review(
            post_id=post_id,
            moderator_id=reviewer_id,
            moderation_status=moderation_status,
            note=note,
        )

        return updated_id

    async def bulk_update_moderation(
        self,
        actor: Actor,
        post_ids: list[UUID],
        moderation_status: ModerationStatus,
        note: str | None = None,
    ) -> BulkModerationResult:
        """
        Decide a selection in one round trip.

        Every id is checked against the caller's scope first: a moderator
        sweeping a selection that happens to include another campus's post
        updates the rest and is told which one was refused, rather than
        having the whole batch fail or -- worse -- quietly go through.
        """
        result = BulkModerationResult()

        found = await self.post_repo.posts_by_ids(post_ids)
        by_id = {post.id: post for post in found}

        allowed: list[UUID] = []

        for post_id in post_ids:
            post = by_id.get(post_id)

            if post is None:
                result.failed.append(
                    BulkModerationFailure(post_id=post_id, reason="not_found")
                )
                continue

            if not actor.can_see_hidden(post.college_id):
                result.failed.append(
                    BulkModerationFailure(post_id=post_id, reason="forbidden")
                )
                continue

            allowed.append(post_id)

        if not allowed:
            return result

        updated = await self.post_repo.set_moderation_status_bulk(
            post_ids=allowed,
            moderation_status=moderation_status,
            reviewer_id=actor.id,
        )

        # Every touched post is invalidated and reindexed, not just the first.
        for post_id in updated:
            await self.post_store.redis_store.delete(str(post_id))
            await self._reindex(post_id)
            await self.logs.log_review(
                post_id=post_id,
                moderator_id=actor.id,
                moderation_status=moderation_status,
                note=note,
            )

        result.updated = updated

        return result

    async def moderation_history(
        self,
        actor: Actor,
        post_id: UUID,
    ) -> list[ModerationLogEntry]:
        """
        Who decided what, and when.

        Readable by the post's author -- so they can see why their post was
        held -- by staff of that post's college, and by an admin. Because the
        author is allowed, this cannot sit behind a plain MODERATE_POST
        guard.
        """
        post = await self.post_repo.get_for_update(post_id)

        if not post:
            raise HTTPException(
                status_code=404,
                detail={"code": "post_not_found", "message": "Post not found"},
            )

        if not (actor.owns(post) or actor.can_see_hidden(post.college_id)):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden",
                    "message": "Not authorized to see this post's history",
                },
            )

        entries = await self.logs.history_for_post(post_id)

        from app.domains.user.hydrate import attach_users

        return await attach_users(
            self.db,
            [ModerationLogEntry.model_validate(e) for e in entries],
            ("moderator_id", "moderator"),
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_post(
        self,
        post_id: UUID,
        moderator_id: UUID | None = None,
        note: str | None = None,
    ) -> list[str]:
        """
        Permanent removal. Authors soft delete instead (status=deleted).

        Returns the Cloudinary ids of the post's media so the caller can move
        them out of the live folder. The files are not destroyed: a takedown
        stays reviewable afterwards.
        """
        db_post = await self.post_repo.get_by_id(post_id)

        if not db_post:
            raise HTTPException(
                status_code=404,
                detail={"code": "post_not_found", "message": "Post not found"},
            )

        public_ids = [m.public_id for m in db_post.media if m.public_id]

        await self.post_store.delete(post_id)
        await self._search().delete_post_search(post_id)

        if moderator_id is not None:
            await self.logs.log_permanent_delete(
                post_id=post_id,
                moderator_id=moderator_id,
                note=note,
            )

        return public_ids
