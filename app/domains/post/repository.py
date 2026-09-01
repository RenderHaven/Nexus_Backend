from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Category, College, ModerationStatus, Post, PostStatus
from app.domains.post.rules import apply_is_active


class PostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _post_options(self):
        return [
            selectinload(Post.media),
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.college),
        ]

    async def create(self, post: Post) -> Post:
        # Single choke point for creation: a new post is always published by
        # its owner, unreviewed, and invisible until a moderator approves it.
        post.status = PostStatus.published
        post.moderation_status = ModerationStatus.pending
        post.is_active = False

        self.db.add(post)
        await self.db.commit()
        return post

    async def update(self, post: Post) -> Post:
        self.db.add(post)
        await self.db.commit()
        return post

    async def delete(self, post: Post) -> Post:
        await self.db.delete(post)
        await self.db.commit()
        return post

    async def exists(self, post_id: UUID) -> bool:
        result = await self.db.execute(
            select(Post.id).where(Post.id == post_id)
        )
        return result.scalar_one_or_none() is not None

    async def category_exists(self, category_id: UUID) -> bool:
        result = await self.db.execute(
            select(Category.id).where(Category.id == category_id)
        )
        return result.scalar_one_or_none() is not None

    async def college_exists(self, college_id: UUID) -> bool:
        result = await self.db.execute(
            select(College.id).where(College.id == college_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_for_update(self, post_id: UUID) -> Post | None:
        """
        Fetch a post without its relationships, for ownership checks and
        column writes. Nothing here needs the author, media or category.
        """
        result = await self.db.execute(
            select(Post).where(Post.id == post_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, post_id: UUID) -> Post | None:
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(Post.id == post_id)
        )
        return result.scalar_one_or_none()

    async def get_one(self) -> Post | None:
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(Post.is_active == True)
            .where(Post.status == PostStatus.published)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_all_posts(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def posts_by_ids(
        self,
        post_ids: list[UUID],
    ) -> list[Post]:
        if not post_ids:
            return []
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(Post.id.in_(post_ids))
        )
        return list(result.scalars().all())
    # =========================
    # Owner scoped
    # =========================

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> list[Post]:
        """
        An author's own posts, straight from the database.

        The public half of this listing is served by the user post pool, so
        callers pass is_active=False to get only the posts that pool cannot
        show: awaiting review, held, or archived.
        """
        conditions = [Post.user_id == user_id]

        if is_active is not None:
            conditions.append(Post.is_active.is_(is_active))

        if not include_deleted:
            conditions.append(Post.status != PostStatus.deleted)

        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(*conditions)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    # =========================
    # Moderation
    # =========================

    async def list_by_moderation_status(
        self,
        moderation_status: ModerationStatus,
        limit: int = 20,
        offset: int = 0,
        college_id: UUID | None = None,
    ) -> list[Post]:
        """
        Moderation queue. Only posts the owner still keeps published are
        listed; archived/deleted posts are not a moderator's problem.
        """
        conditions = [
            Post.moderation_status == moderation_status,
            Post.status == PostStatus.published,
        ]

        if college_id is not None:
            conditions.append(Post.college_id == college_id)

        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(*conditions)
            .order_by(Post.created_at.asc(), Post.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def set_moderation_status(
        self,
        post_id: UUID,
        moderation_status: ModerationStatus,
        reviewer_id: UUID,
    ) -> UUID | None:
        post = await self.get_for_update(post_id)
        if not post:
            return None

        post.moderation_status = moderation_status
        post.reviewed_by = reviewer_id
        post.reviewed_at = datetime.now(timezone.utc)
        apply_is_active(post)

        await self.db.commit()
        return post_id

    async def set_status(
        self,
        post_id: UUID,
        status: PostStatus,
    ) -> UUID | None:
        post = await self.get_for_update(post_id)
        if not post:
            return None

        post.status = status
        apply_is_active(post)

        await self.db.commit()
        return post_id
