from uuid import UUID

from fastapi import HTTPException

from app.db.models import ModerationStatus
from app.domains.logs import ModerationLogService
from app.domains.post.schemas import Post
from app.domains.post.service import PostService
from app.domains.post.storage import PostStorage
from app.rules import Permission, require_permission

# Re-exported so callers can keep importing these from the post domain, but
# the rules themselves live in app/rules.
from app.rules import RESTRICTED_POST_TYPES  # noqa: F401


def require_moderator(user):
    """Raise unless the user may moderate posts."""
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

        await self.logs.log_restricted_create(
            post_id=db_post.id,
            moderator_id=post.user_id,
            post_type=getattr(post.type, "value", str(post.type)),
        )

        return db_post.id

    # ------------------------------------------------------------------
    # Moderation
    # ------------------------------------------------------------------

    async def list_by_moderation_status(
        self,
        moderation_status: ModerationStatus,
        limit: int = 20,
        offset: int = 0,
        college_id: UUID | None = None,
    ) -> list[Post]:
        db_posts = await self.post_repo.list_by_moderation_status(
            moderation_status=moderation_status,
            limit=limit,
            offset=offset,
            college_id=college_id,
        )
        return [Post.model_validate(p) for p in db_posts]

    async def update_moderation_status(
        self,
        post_id: UUID,
        moderation_status: ModerationStatus,
        reviewer_id: UUID,
        note: str | None = None,
    ) -> UUID:
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

        await self.logs.log_review(
            post_id=post_id,
            moderator_id=reviewer_id,
            moderation_status=moderation_status,
            note=note,
        )

        return updated_id

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

        if moderator_id is not None:
            await self.logs.log_permanent_delete(
                post_id=post_id,
                moderator_id=moderator_id,
                note=note,
            )

        return public_ids
