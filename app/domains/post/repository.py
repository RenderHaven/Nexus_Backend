from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.db.models import Category, College, ModerationStatus, Post, PostStatus, User
from app.domains.post.rules import apply_is_active


class PostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _post_options(self):
        """
        What every post read loads: the post's own row plus its media, which
        the post owns and which has no life outside it.

        author, category and college are deliberately absent. They are
        references, not parts of a post, and are resolved from their own
        caches at read time -- see PostService._hydrate_references. Joining
        them here is what made a renamed college keep serving its old name
        out of every post that had embedded it. noload rather than plain
        omission so validating the row cannot trip a lazy load on the async
        session.
        """
        return [
            selectinload(Post.media),
            noload(Post.author),
            noload(Post.category),
            noload(Post.college),
        ]

    # =========================
    # Bulk / index reads
    #
    # Flat column selects, never ORM objects: a caller walking the whole table
    # must not trigger a lazy load per row. Columns of `posts` only -- no join
    # to users. A consumer that needs the author's name resolves it from
    # user_id against the entity cache, so a rename is one cache delete rather
    # than a fan-out over every post that person wrote.
    # =========================

    def _flat_select(self):
        return select(
            Post.id,
            Post.title,
            Post.content,
            Post.type,
            Post.user_id,
            Post.college_id,
            Post.category_id,
            Post.is_active,
            Post.status,
            Post.created_at,
            Post.engagement_score,
        )

    async def get_post_row(self, post_id: UUID):
        """One post in the flat shape, for a single-document reindex."""
        result = await self.db.execute(
            self._flat_select().where(Post.id == post_id)
        )
        return result.one_or_none()

    async def get_all_posts(
        self,
        after: tuple | None = None,
        limit: int = 1000,
        is_active: bool | None = None,
    ) -> list:
        """
        One keyset page of every post worth exporting, ordered by
        (created_at, id). Pass the last row's (created_at, id) back as `after`
        to get the next page.

        Keyset rather than OFFSET: a full table walk with OFFSET re-scans and
        discards everything before the page, so it degrades quadratically.

        Deleted posts are always skipped. Pass is_active=True for only the
        publicly visible ones -- that is what the search rebuild does, so the
        index never holds a post a reader is not allowed to see.
        """
        query = (
            self._flat_select()
            .where(Post.status != PostStatus.deleted)
            .order_by(Post.created_at, Post.id)
            .limit(limit)
        )

        if is_active is not None:
            query = query.where(Post.is_active.is_(is_active))

        if after is not None:
            query = query.where(tuple_(Post.created_at, Post.id) > after)

        return list((await self.db.execute(query)).all())

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
        """One post as a flat row plus media. See _post_options."""
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
        """Flat rows plus media, for the cache backfill. See _post_options."""
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

    # Columns the queue may be ordered by. The caller sends a key from
    # ModerationSort, never a column name, so nothing user-supplied ever
    # reaches the ORDER BY.
    _QUEUE_SORTS = {
        "created_at": Post.created_at,
        "reviewed_at": Post.reviewed_at,
        "engagement": Post.engagement_score,
    }

    def _moderation_conditions(
        self,
        moderation_status: ModerationStatus,
        college_id: UUID | None = None,
        user_id: UUID | None = None,
        category_id: UUID | None = None,
        post_type=None,
        q: str | None = None,
        date_from=None,
        date_to=None,
    ) -> list:
        """
        The queue's WHERE clause, built once so the listing and the counts can
        never disagree about what is in the queue.

        Only posts the owner still keeps published are listed; archived and
        deleted posts are not a moderator's problem.
        """
        conditions = [
            Post.moderation_status == moderation_status,
            Post.status == PostStatus.published,
        ]

        if college_id is not None:
            conditions.append(Post.college_id == college_id)

        if user_id is not None:
            conditions.append(Post.user_id == user_id)

        if category_id is not None:
            conditions.append(Post.category_id == category_id)

        if post_type is not None:
            conditions.append(Post.type == post_type)

        if date_from is not None:
            conditions.append(Post.created_at >= date_from)

        if date_to is not None:
            conditions.append(Post.created_at <= date_to)

        if q:
            # escape the LIKE wildcards so a literal % in a search box does
            # not turn into "match everything".
            term = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{term}%"
            conditions.append(
                or_(
                    Post.title.ilike(pattern, escape="\\"),
                    Post.content.ilike(pattern, escape="\\"),
                )
            )

        return conditions

    async def list_by_moderation_status(
        self,
        moderation_status: ModerationStatus,
        limit: int = 20,
        offset: int = 0,
        college_id: UUID | None = None,
        user_id: UUID | None = None,
        category_id: UUID | None = None,
        post_type=None,
        q: str | None = None,
        date_from=None,
        date_to=None,
        sort: str = "created_at",
        order: str = "asc",
    ) -> list[Post]:
        """
        Moderation queue, filtered and sorted for the review table.

        The id is always the last sort key so a page boundary is stable when
        many rows share a timestamp.
        """
        conditions = self._moderation_conditions(
            moderation_status=moderation_status,
            college_id=college_id,
            user_id=user_id,
            category_id=category_id,
            post_type=post_type,
            q=q,
            date_from=date_from,
            date_to=date_to,
        )

        column = self._QUEUE_SORTS.get(sort, Post.created_at)
        direction = (
            (lambda c: c.desc()) if order == "desc" else (lambda c: c.asc())
        )

        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(*conditions)
            .order_by(direction(column), direction(Post.id))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def counts_by_moderation_status(
        self,
        college_id: UUID | None = None,
    ) -> dict[ModerationStatus, int]:
        """
        Every status total in one grouped count, for the queue tab badges.

        Statuses with no rows are absent from the result rather than zero, so
        callers should read it with .get().
        """
        query = (
            select(Post.moderation_status, func.count(Post.id))
            .where(Post.status == PostStatus.published)
            .group_by(Post.moderation_status)
        )

        if college_id is not None:
            query = query.where(Post.college_id == college_id)

        return {row[0]: row[1] for row in (await self.db.execute(query)).all()}

    async def _author_is_active(self, user_id: UUID) -> bool:
        """
        Whether a post's author still has a live account.

        Approving the post of a deactivated user must not put it back in
        front of readers, so every moderation write asks this first.
        """
        result = await self.db.execute(
            select(User.is_active).where(User.id == user_id)
        )
        row = result.scalar_one_or_none()
        return bool(row) if row is not None else True

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
        apply_is_active(post, await self._author_is_active(post.user_id))

        await self.db.commit()
        return post_id

    async def set_moderation_status_bulk(
        self,
        post_ids: list[UUID],
        moderation_status: ModerationStatus,
        reviewer_id: UUID,
    ) -> list[UUID]:
        """
        Decide several posts at once, in one transaction.

        Ids that do not exist are simply absent from the return value -- one
        bad id must not sink the whole batch. is_active still goes through
        apply_is_active rather than being set here, so the derivation of
        "publicly visible" stays in one place.
        """
        if not post_ids:
            return []

        result = await self.db.execute(
            select(Post).where(Post.id.in_(post_ids))
        )
        posts = list(result.scalars().all())

        if not posts:
            return []

        reviewed_at = datetime.now(timezone.utc)

        # One lookup for the whole batch rather than one per post.
        author_ids = {post.user_id for post in posts}
        active_authors = await self._active_authors(author_ids)

        for post in posts:
            post.moderation_status = moderation_status
            post.reviewed_by = reviewer_id
            post.reviewed_at = reviewed_at
            apply_is_active(post, post.user_id in active_authors)

        await self.db.commit()

        return [post.id for post in posts]

    async def set_status(
        self,
        post_id: UUID,
        status: PostStatus,
    ) -> UUID | None:
        post = await self.get_for_update(post_id)
        if not post:
            return None

        post.status = status
        apply_is_active(post, await self._author_is_active(post.user_id))

        await self.db.commit()
        return post_id

    async def _active_authors(self, user_ids) -> set:
        """Which of these users still have a live account."""
        if not user_ids:
            return set()

        result = await self.db.execute(
            select(User.id).where(
                User.id.in_(list(user_ids)),
                User.is_active.is_(True),
            )
        )
        return set(result.scalars().all())

    # =========================
    # Author account state
    # =========================

    async def set_author_posts_visibility(
        self,
        user_id: UUID,
        author_is_active: bool,
    ) -> list[UUID]:
        """
        Recompute is_active across everything one author has written, after
        their account was deactivated or brought back.

        Returns the ids whose visibility actually changed, so the caller
        reindexes and busts only those rather than the author's whole
        history.
        """
        result = await self.db.execute(
            select(Post).where(Post.user_id == user_id)
        )
        posts = list(result.scalars().all())

        changed: list[UUID] = []

        for post in posts:
            before = post.is_active
            apply_is_active(post, author_is_active)
            if post.is_active != before:
                changed.append(post.id)

        if changed:
            await self.db.commit()

        return changed
