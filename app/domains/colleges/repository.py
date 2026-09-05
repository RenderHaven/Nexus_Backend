from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import College, ModerationStatus, Post, PostStatus, User
from .schemas import CollegeBasic

class CollegeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        result = await self.db.execute(select(College).where(College.id == college_id))
        college = result.scalars().first()
        if not college:
            return None
        return CollegeBasic.model_validate(college)

    async def get_colleges(self) -> list[CollegeBasic]:
        """
        Every college, ordered by name.

        Unpaginated on purpose: this is a bounded reference table a client
        renders whole -- a signup picker, a moderation filter. If it ever
        stops being small enough to send in one response, it needs a cursor
        rather than a bigger limit.
        """
        result = await self.db.execute(
            select(College).order_by(College.name.asc())
        )
        return [CollegeBasic.model_validate(c) for c in result.scalars().all()]

    async def colleges_by_ids(self, college_ids: list[UUID]) -> list[CollegeBasic]:
        """
        Full rows for a set of ids, for hydrating a page of posts or users.

        Full rows on purpose, not _flat_select(): whatever this returns is
        written back to college:{id}, and a projection would leave a blob
        that the next CollegeBasic read validates against silently, filling
        in defaults for the columns it dropped.
        """
        if not college_ids:
            return []

        result = await self.db.execute(
            select(College).where(College.id.in_(college_ids))
        )
        return [CollegeBasic.model_validate(c) for c in result.scalars().all()]

    # ------------------------------------------------------------------
    # Bulk / index reads
    # ------------------------------------------------------------------

    def _flat_select(self):
        return select(
            College.id,
            College.name,
            College.tagline,
            College.location,
            College.created_at,
        )

    async def get_college_row(self, college_id: UUID):
        result = await self.db.execute(
            self._flat_select().where(College.id == college_id)
        )
        return result.one_or_none()

    async def get_all_colleges(
        self,
        after: tuple | None = None,
        limit: int = 1000,
    ) -> list:
        """
        One keyset page of every college as flat rows.

        Distinct from get_colleges(), which returns validated CollegeBasic
        models for an API response. This one is for walking the table.
        """
        query = (
            self._flat_select()
            .order_by(College.created_at, College.id)
            .limit(limit)
        )

        if after is not None:
            query = query.where(tuple_(College.created_at, College.id) > after)

        return list((await self.db.execute(query)).all())

    async def get_for_update(self, college_id: UUID) -> College | None:
        result = await self.db.execute(select(College).where(College.id == college_id))
        return result.scalars().first()

    async def create(self, values: dict) -> College:
        college = College(id=uuid4(), **values)
        self.db.add(college)
        await self.db.commit()
        return college

    async def update(self, college_id: UUID, changes: dict) -> UUID | None:
        college = await self.get_for_update(college_id)

        if not college:
            return None

        for field, value in changes.items():
            setattr(college, field, value)

        await self.db.commit()
        return college_id

    async def get_posts(self, college_id: UUID, limit: int) -> list[Post]:
        result = await self.db.execute(
            select(Post)
            .where(Post.college_id == college_id)
            .where(Post.is_active.is_(True))
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_users(
        self,
        college_id: UUID,
        limit: int,
        role=None,
        is_alumni: bool | None = None,
        q: str | None = None,
    ) -> list[User]:
        """
        People on one campus, newest first.

        Deactivated accounts are excluded. Their posts are already out of the
        feed and they are out of the search index, so leaving them in the
        campus people list would be the one place a disabled account still
        showed up.
        """
        conditions = [
            User.college_id == college_id,
            User.is_active.is_(True),
        ]

        if role is not None:
            conditions.append(User.role == role)

        if is_alumni is not None:
            conditions.append(User.is_alumni.is_(is_alumni))

        if q:
            term = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(User.username.ilike(f"%{term}%", escape="\\"))

        result = await self.db.execute(
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc(), User.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Admin table
    # ------------------------------------------------------------------

    _LIST_SORTS = {
        "name": College.name,
        "created_at": College.created_at,
    }

    async def list_colleges(
        self,
        limit: int = 20,
        offset: int = 0,
        college_id: UUID | None = None,
        q: str | None = None,
        sort: str = "name",
        order: str = "asc",
    ) -> list[College]:
        """
        One page of the admin college table.

        Separate from get_colleges(), which stays the unpaginated public
        picker the signup flow reads before anyone is authenticated.

        college_id narrows to a single row -- that is how a moderator sees
        their own campus and nothing else.

        user_count and post_count are not joined here: counting inline would
        make this a scan per row. counts_for_all() fetches them in one
        grouped query and the service stitches the two together.
        """
        conditions = []

        if college_id is not None:
            conditions.append(College.id == college_id)

        if q:
            term = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{term}%"
            conditions.append(
                or_(
                    College.name.ilike(pattern, escape="\\"),
                    College.location.ilike(pattern, escape="\\"),
                )
            )

        column = self._LIST_SORTS.get(sort, College.name)
        direction = (
            (lambda c: c.desc()) if order == "desc" else (lambda c: c.asc())
        )

        result = await self.db.execute(
            select(College)
            .where(*conditions)
            .order_by(direction(column), direction(College.id))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    async def counts_for_all(
        self,
        college_ids: list[UUID] | None = None,
    ) -> dict[UUID, dict[str, int]]:
        """
        Members and posts per college, in two grouped queries rather than
        two per row.

        Only live accounts and publicly visible posts are counted, so the
        number on an admin row means the same thing as what a visitor sees.
        """
        counts: dict[UUID, dict[str, int]] = {}

        def bucket(cid):
            return counts.setdefault(
                cid, {"user_count": 0, "post_count": 0, "pending_count": 0}
            )

        user_q = (
            select(User.college_id, func.count(User.id))
            .where(User.is_active.is_(True))
            .group_by(User.college_id)
        )
        post_q = (
            select(
                Post.college_id,
                func.count(Post.id).filter(Post.is_active.is_(True)),
                func.count(Post.id).filter(
                    Post.moderation_status == ModerationStatus.pending,
                    Post.status == PostStatus.published,
                ),
            )
            .group_by(Post.college_id)
        )

        if college_ids:
            user_q = user_q.where(User.college_id.in_(college_ids))
            post_q = post_q.where(Post.college_id.in_(college_ids))

        for cid, n in (await self.db.execute(user_q)).all():
            bucket(cid)["user_count"] = n or 0

        for cid, active, pending in (await self.db.execute(post_q)).all():
            row = bucket(cid)
            row["post_count"] = active or 0
            row["pending_count"] = pending or 0

        return counts

    async def counts_for(self, college_id: UUID) -> dict[str, int]:
        """One college's headline numbers, plus how many people were active
        in the last week."""
        counts = (await self.counts_for_all([college_id])).get(
            college_id, {"user_count": 0, "post_count": 0, "pending_count": 0}
        )

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # "Active" is approximated by having posted -- there is no last-seen
        # signal yet, so this undercounts people who only read.
        result = await self.db.execute(
            select(func.count(func.distinct(Post.user_id))).where(
                Post.college_id == college_id,
                Post.created_at >= week_ago,
            )
        )

        return {
            "users": counts["user_count"],
            "posts": counts["post_count"],
            "pending": counts["pending_count"],
            "active_this_week": result.scalar_one() or 0,
        }

    async def references(self, college_id: UUID) -> dict[str, int]:
        """
        What still points at this college. Delete is refused while any of
        these is non-zero: users.college_id and posts.college_id are both NOT
        NULL, so the delete would fail on a foreign key anyway.
        """
        out = {}

        for key, column in (
            ("users", User.college_id),
            ("posts", Post.college_id),
            ("restricted_posts", Post.restricted_to_college_id),
        ):
            model = User if key == "users" else Post
            result = await self.db.execute(
                select(func.count(model.id)).where(column == college_id)
            )
            out[key] = result.scalar_one() or 0

        return out

    async def delete(self, college_id: UUID) -> bool:
        college = await self.get_for_update(college_id)

        if not college:
            return False

        await self.db.delete(college)
        await self.db.commit()
        return True
