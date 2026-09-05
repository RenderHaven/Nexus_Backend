"""
Dashboard numbers.

Every method here does the same two things before it reads anything:

    college_id = actor.scope_college(college_id)
    actor.require(Permission.VIEW_COLLEGE_STATS, college_id)

That pair is the whole authorisation story. An admin may pass any college or
none at all, and None means the platform-wide figure. A moderator or success
coach gets their own campus filled in when they ask for nothing, and a 403 if
they name another. No statistic can be produced for a college the caller
cannot see.
"""
from uuid import UUID

from app.domains.stats.repository import StatsRepository, range_start
from app.domains.stats.schemas import (
    ActivityEntry,
    BreakdownSlice,
    CollegeRollup,
    ModerationStats,
    Overview,
    PostsBucket,
    TopPost,
    TopUser,
    UsersBucket,
)
from app.rules import Actor, Permission


class StatsService:

    def __init__(self, db):
        self.db = db
        self.repo = StatsRepository(db)

    def _scope(self, actor: Actor, college_id: UUID | None) -> UUID | None:
        college_id = actor.scope_college(college_id)
        actor.require(Permission.VIEW_COLLEGE_STATS, college_id)
        return college_id

    # ------------------------------------------------------------------

    async def overview(self, actor: Actor, college_id: UUID | None = None) -> Overview:
        college_id = self._scope(actor, college_id)
        return Overview(**await self.repo.overview(college_id))

    async def posts_timeseries(
        self,
        actor: Actor,
        college_id: UUID | None = None,
        range_key: str = "30d",
        interval: str = "day",
    ) -> list[PostsBucket]:
        college_id = self._scope(actor, college_id)

        rows = await self.repo.posts_timeseries(
            college_id=college_id,
            interval=interval,
            since=range_start(range_key),
        )
        return [PostsBucket(**r) for r in rows]

    async def users_timeseries(
        self,
        actor: Actor,
        college_id: UUID | None = None,
        range_key: str = "30d",
        interval: str = "day",
        split_by_role: bool = False,
    ) -> list[UsersBucket]:
        college_id = self._scope(actor, college_id)

        rows = await self.repo.users_timeseries(
            college_id=college_id,
            interval=interval,
            since=range_start(range_key),
            split_by_role=split_by_role,
        )
        return [UsersBucket(**r) for r in rows]

    async def moderation(
        self,
        actor: Actor,
        college_id: UUID | None = None,
        range_key: str = "30d",
    ) -> ModerationStats:
        college_id = self._scope(actor, college_id)

        return ModerationStats(
            **await self.repo.moderation_stats(
                college_id=college_id,
                since=range_start(range_key),
            )
        )

    async def post_breakdown(
        self,
        actor: Actor,
        group_by: str = "type",
        college_id: UUID | None = None,
        range_key: str = "30d",
    ) -> list[BreakdownSlice]:
        college_id = self._scope(actor, college_id)

        rows = await self.repo.post_breakdown(
            college_id=college_id,
            group_by=group_by,
            since=range_start(range_key),
        )
        return [BreakdownSlice(**r) for r in rows]

    async def top_posts(
        self,
        actor: Actor,
        metric: str = "engagement",
        college_id: UUID | None = None,
        range_key: str = "30d",
        limit: int = 10,
    ) -> list[TopPost]:
        college_id = self._scope(actor, college_id)

        posts = await self.repo.top_posts(
            college_id=college_id,
            metric=metric,
            since=range_start(range_key),
            limit=limit,
        )
        return [TopPost.model_validate(p) for p in posts]

    async def top_users(
        self,
        actor: Actor,
        metric: str = "posts",
        college_id: UUID | None = None,
        range_key: str = "30d",
        limit: int = 10,
    ) -> list[TopUser]:
        college_id = self._scope(actor, college_id)

        rows = await self.repo.top_users(
            college_id=college_id,
            metric=metric,
            since=range_start(range_key),
            limit=limit,
        )
        return [TopUser(**r) for r in rows]

    async def colleges_rollup(self, actor: Actor) -> list[CollegeRollup]:
        """
        One row per college: members, posts, pending.

        Reuses the college domain's own counts so this table and the
        Manage-Colleges screen can never disagree.
        """
        actor.require(Permission.VIEW_COLLEGE_STATS, actor.college_id)

        from app.domains.colleges.repository import CollegeRepository

        college_repo = CollegeRepository(self.db)

        # A moderator's rollup is their own campus; an admin's is everything.
        only = None if actor.is_platform_wide else actor.college_id

        colleges = await college_repo.list_colleges(
            limit=500,
            college_id=only,
            sort="name",
        )

        if not colleges:
            return []

        counts = await college_repo.counts_for_all([c.id for c in colleges])

        return [
            CollegeRollup(
                college_id=c.id,
                name=c.name,
                users=counts.get(c.id, {}).get("user_count", 0),
                posts=counts.get(c.id, {}).get("post_count", 0),
                pending=counts.get(c.id, {}).get("pending_count", 0),
            )
            for c in colleges
        ]

    async def activity(
        self,
        actor: Actor,
        college_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityEntry]:
        college_id = self._scope(actor, college_id)

        rows = await self.repo.recent_activity(
            college_id=college_id,
            limit=limit,
            offset=offset,
        )
        return [ActivityEntry(**r) for r in rows]
