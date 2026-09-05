"""
Aggregate reads for the dashboard.

Everything is counted live. Each method takes an already-scoped college_id --
the service resolves it from the caller before anything here runs, so a
None here means "every college" and only an admin can produce one.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Category,
    College,
    ModerationLog,
    ModerationStatus,
    Post,
    PostStatus,
    User,
)

# How far back each range reaches. `all` has no floor.
RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "all": None}


def range_start(range_key: str) -> datetime | None:
    days = RANGE_DAYS.get(range_key, 30)
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


class StatsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    async def overview(self, college_id: UUID | None) -> dict[str, int]:
        """
        The headline counters.

        Only live accounts and publicly visible posts are counted, so these
        agree with what the rest of the app shows.
        """
        def scoped(query, column):
            return query if college_id is None else query.where(column == college_id)

        users = await self.db.execute(
            scoped(
                select(func.count(User.id)).where(User.is_active.is_(True)),
                User.college_id,
            )
        )

        colleges = await self.db.execute(
            select(func.count(College.id))
            if college_id is None
            else select(func.count(College.id)).where(College.id == college_id)
        )

        posts = await self.db.execute(
            scoped(
                select(func.count(Post.id)).where(Post.is_active.is_(True)),
                Post.college_id,
            )
        )

        pending = await self.db.execute(
            scoped(
                select(func.count(Post.id)).where(
                    Post.moderation_status == ModerationStatus.pending,
                    Post.status == PostStatus.published,
                ),
                Post.college_id,
            )
        )

        # No last-seen signal exists, so "active" means posted today. This
        # undercounts anyone who only read.
        since = datetime.now(timezone.utc) - timedelta(days=1)
        active = await self.db.execute(
            scoped(
                select(func.count(func.distinct(Post.user_id))).where(
                    Post.created_at >= since
                ),
                Post.college_id,
            )
        )

        return {
            "users": users.scalar_one() or 0,
            "colleges": colleges.scalar_one() or 0,
            "posts": posts.scalar_one() or 0,
            "pending": pending.scalar_one() or 0,
            "active_today": active.scalar_one() or 0,
        }

    # ------------------------------------------------------------------
    # Timeseries
    # ------------------------------------------------------------------

    async def posts_timeseries(
        self,
        college_id: UUID | None,
        interval: str,
        since: datetime | None,
    ) -> list[dict]:
        """
        Posts created, approved and removed per bucket.

        Created is bucketed by created_at; approved and removed by
        reviewed_at, because a decision belongs to the day it was made, not
        the day the post arrived. The two are gathered separately and merged
        on the bucket.
        """
        buckets: dict = {}

        def row(key):
            return buckets.setdefault(
                key, {"bucket": key, "created": 0, "approved": 0, "removed": 0}
            )

        created_bucket = func.date_trunc(interval, Post.created_at).label("b")
        q = select(created_bucket, func.count(Post.id)).group_by(created_bucket)

        if college_id is not None:
            q = q.where(Post.college_id == college_id)
        if since is not None:
            q = q.where(Post.created_at >= since)

        for bucket, count in (await self.db.execute(q)).all():
            row(bucket)["created"] = count or 0

        reviewed_bucket = func.date_trunc(interval, Post.reviewed_at).label("b")
        q = (
            select(
                reviewed_bucket,
                func.count(Post.id).filter(
                    Post.moderation_status == ModerationStatus.approved
                ),
                func.count(Post.id).filter(
                    Post.moderation_status == ModerationStatus.removed
                ),
            )
            .where(Post.reviewed_at.is_not(None))
            .group_by(reviewed_bucket)
        )

        if college_id is not None:
            q = q.where(Post.college_id == college_id)
        if since is not None:
            q = q.where(Post.reviewed_at >= since)

        for bucket, approved, removed in (await self.db.execute(q)).all():
            entry = row(bucket)
            entry["approved"] = approved or 0
            entry["removed"] = removed or 0

        return [buckets[k] for k in sorted(buckets)]

    async def users_timeseries(
        self,
        college_id: UUID | None,
        interval: str,
        since: datetime | None,
        split_by_role: bool = False,
    ) -> list[dict]:
        """Signups per bucket, optionally split by role."""
        bucket = func.date_trunc(interval, User.created_at).label("b")

        columns = [bucket, func.count(User.id)]
        group = [bucket]

        if split_by_role:
            columns.insert(1, User.role)
            group.append(User.role)

        q = select(*columns).group_by(*group)

        if college_id is not None:
            q = q.where(User.college_id == college_id)
        if since is not None:
            q = q.where(User.created_at >= since)

        out: dict = {}

        for row in (await self.db.execute(q)).all():
            key = row[0]
            entry = out.setdefault(
                key, {"bucket": key, "signups": 0, "by_role": {}}
            )
            count = row[-1] or 0
            entry["signups"] += count
            if split_by_role:
                entry["by_role"][getattr(row[1], "value", str(row[1]))] = count

        return [out[k] for k in sorted(out)]

    # ------------------------------------------------------------------
    # Moderation
    # ------------------------------------------------------------------

    async def moderation_stats(
        self,
        college_id: UUID | None,
        since: datetime | None,
    ) -> dict:
        counts_q = (
            select(Post.moderation_status, func.count(Post.id))
            .where(Post.status == PostStatus.published)
            .group_by(Post.moderation_status)
        )
        if college_id is not None:
            counts_q = counts_q.where(Post.college_id == college_id)

        counts = {
            getattr(status, "value", str(status)): n
            for status, n in (await self.db.execute(counts_q)).all()
        }

        # Median rather than mean: one post left sitting for a month would
        # drag an average far away from what the queue actually feels like.
        seconds = func.extract("epoch", Post.reviewed_at - Post.created_at)
        median_q = select(
            func.percentile_cont(0.5).within_group(cast(seconds, Float))
        ).where(Post.reviewed_at.is_not(None))

        if college_id is not None:
            median_q = median_q.where(Post.college_id == college_id)
        if since is not None:
            median_q = median_q.where(Post.reviewed_at >= since)

        median_seconds = (await self.db.execute(median_q)).scalar_one_or_none()

        by_mod_q = (
            select(
                ModerationLog.coach_id,
                User.username,
                func.count(ModerationLog.id),
            )
            .join(User, User.id == ModerationLog.coach_id)
            .group_by(ModerationLog.coach_id, User.username)
            .order_by(func.count(ModerationLog.id).desc())
        )

        if since is not None:
            by_mod_q = by_mod_q.where(ModerationLog.created_at >= since)
        if college_id is not None:
            by_mod_q = by_mod_q.join(
                Post, Post.id == ModerationLog.post_id
            ).where(Post.college_id == college_id)

        by_moderator = [
            {"moderator_id": mid, "username": name, "decisions": n}
            for mid, name, n in (await self.db.execute(by_mod_q)).all()
        ]

        return {
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "hold": counts.get("hold", 0),
            "removed": counts.get("removed", 0),
            "median_minutes_to_decision": (
                round(median_seconds / 60, 1) if median_seconds is not None else None
            ),
            "by_moderator": by_moderator,
        }

    # ------------------------------------------------------------------
    # Breakdown and leaderboards
    # ------------------------------------------------------------------

    async def post_breakdown(
        self,
        college_id: UUID | None,
        group_by: str,
        since: datetime | None,
    ) -> list[dict]:
        """Publicly visible posts per type, category or college."""
        if group_by == "category":
            key_col, label_col, join = Post.category_id, Category.name, Category
        elif group_by == "college":
            key_col, label_col, join = Post.college_id, College.name, College
        else:
            key_col, label_col, join = Post.type, None, None

        columns = [key_col, func.count(Post.id)]
        group = [key_col]

        if label_col is not None:
            columns.insert(1, label_col)
            group.append(label_col)

        q = select(*columns).where(Post.is_active.is_(True))

        if join is not None:
            q = q.join(join, join.id == key_col)

        q = q.group_by(*group).order_by(func.count(Post.id).desc())

        if college_id is not None:
            q = q.where(Post.college_id == college_id)
        if since is not None:
            q = q.where(Post.created_at >= since)

        out = []

        for row in (await self.db.execute(q)).all():
            key = row[0]
            out.append(
                {
                    "key": getattr(key, "value", str(key)),
                    "label": row[1] if label_col is not None else None,
                    "count": row[-1] or 0,
                }
            )

        return out

    _TOP_POST_METRICS = {
        "engagement": Post.engagement_score,
        "likes": Post.like_count,
        "comments": Post.comment_count,
    }

    async def top_posts(
        self,
        college_id: UUID | None,
        metric: str,
        since: datetime | None,
        limit: int,
    ) -> list[Post]:
        column = self._TOP_POST_METRICS.get(metric, Post.engagement_score)

        q = (
            select(Post)
            .where(Post.is_active.is_(True))
            .order_by(column.desc(), Post.id.desc())
            .limit(limit)
        )

        if college_id is not None:
            q = q.where(Post.college_id == college_id)
        if since is not None:
            q = q.where(Post.created_at >= since)

        return list((await self.db.execute(q)).scalars().all())

    async def top_users(
        self,
        college_id: UUID | None,
        metric: str,
        since: datetime | None,
        limit: int,
    ) -> list[dict]:
        """
        Most active contributors.

        post_count is always returned, whichever metric orders the list, so
        the table can show both columns from one call.
        """
        post_count = func.count(Post.id).label("post_count")

        post_join = Post.user_id == User.id
        if since is not None:
            post_join = post_join & (Post.created_at >= since)

        q = (
            select(User, post_count)
            .outerjoin(Post, post_join)
            .where(User.is_active.is_(True))
            .group_by(User.id)
            .limit(limit)
        )

        q = q.order_by(
            User.total_xp.desc() if metric == "xp" else post_count.desc(),
            User.id.desc(),
        )

        if college_id is not None:
            q = q.where(User.college_id == college_id)

        return [
            {
                "id": user.id,
                "username": user.username,
                "college_id": user.college_id,
                "role": user.role,
                "total_xp": user.total_xp,
                "post_count": count or 0,
            }
            for user, count in (await self.db.execute(q)).all()
        ]

    # ------------------------------------------------------------------
    # Activity
    # ------------------------------------------------------------------

    async def recent_activity(
        self,
        college_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """
        Staff actions, newest first.

        Scoped by the college of the post that was acted on rather than the
        moderator's own, so an admin working on campus B shows up in campus
        B's feed.
        """
        q = (
            select(
                ModerationLog.id,
                ModerationLog.action,
                ModerationLog.post_id,
                Post.college_id,
                ModerationLog.coach_id,
                User.username,
                ModerationLog.note,
                ModerationLog.created_at,
            )
            .join(Post, Post.id == ModerationLog.post_id)
            .join(User, User.id == ModerationLog.coach_id)
            .order_by(ModerationLog.created_at.desc(), ModerationLog.id.desc())
            .offset(offset)
            .limit(limit)
        )

        if college_id is not None:
            q = q.where(Post.college_id == college_id)

        return [
            {
                "id": r[0],
                "action": r[1],
                "post_id": r[2],
                "college_id": r[3],
                "moderator_id": r[4],
                "moderator_username": r[5],
                "note": r[6],
                "created_at": r[7],
            }
            for r in (await self.db.execute(q)).all()
        ]
