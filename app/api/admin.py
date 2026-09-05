"""
The admin dashboard.

Read-only. Every route is staff, and every one is scoped the same way: leave
college_id out and your own campus is filled in; an admin may name any
college, or omit it for the platform-wide figure.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_actor
from app.db.session import get_db
from app.domains.stats.schemas import (
    ActivityEntry,
    BreakdownBy,
    BreakdownSlice,
    CollegeRollup,
    Interval,
    ModerationStats,
    Overview,
    PostsBucket,
    StatsRange,
    TopPost,
    TopPostMetric,
    TopUser,
    TopUserMetric,
    UsersBucket,
)
from app.domains.stats.service import StatsService
from app.rules import Actor, Permission

router = APIRouter()


async def get_stats_actor(actor: Actor = Depends(get_actor)) -> Actor:
    """Admins, moderators and success coaches. The college is decided per
    request by the service."""
    actor.require(Permission.VIEW_COLLEGE_STATS)
    return actor


@router.get("/stats/overview", response_model=Overview)
async def get_overview(
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """The headline counters: members, colleges, posts, queue and who posted
    today.

    Scoped to your own college unless you are an admin, who gets the
    platform-wide figures by default and one campus by passing college_id."""
    return await StatsService(db).overview(staff, college_id)


@router.get("/stats/posts_timeseries", response_model=list[PostsBucket])
async def get_posts_timeseries(
    range: StatsRange = StatsRange.d30,
    interval: Interval = Interval.day,
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Posts created, approved and removed per bucket.

    Created counts by the day a post arrived; approved and removed count by
    the day the decision was made, so a backlog cleared on Friday shows on
    Friday. Buckets with no activity are absent rather than zero."""
    return await StatsService(db).posts_timeseries(
        staff, college_id, range.value, interval.value
    )


@router.get("/stats/users_timeseries", response_model=list[UsersBucket])
async def get_users_timeseries(
    range: StatsRange = StatsRange.d30,
    interval: Interval = Interval.day,
    split_by_role: bool = False,
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Signups per bucket, optionally split by role."""
    return await StatsService(db).users_timeseries(
        staff, college_id, range.value, interval.value, split_by_role
    )


@router.get("/stats/moderation", response_model=ModerationStats)
async def get_moderation_stats(
    range: StatsRange = StatsRange.d30,
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Queue health: how much sits in each state, the median time to a
    decision, and how many decisions each moderator made.

    The median is taken over posts actually decided in the range -- anything
    still waiting has no decision time and shows up in pending instead.
    Per-moderator figures come from the audit trail, which has no history
    before it started being written."""
    return await StatsService(db).moderation(staff, college_id, range.value)


@router.get("/stats/post_breakdown", response_model=list[BreakdownSlice])
async def get_post_breakdown(
    group_by: BreakdownBy = BreakdownBy.type,
    range: StatsRange = StatsRange.d30,
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Publicly visible posts grouped by type, category or campus. Backs the
    donut and bar charts."""
    return await StatsService(db).post_breakdown(
        staff, group_by.value, college_id, range.value
    )


@router.get("/stats/top_posts", response_model=list[TopPost])
async def get_top_posts(
    metric: TopPostMetric = TopPostMetric.engagement,
    range: StatsRange = StatsRange.d30,
    limit: int = Query(10, ge=1, le=50),
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Best-performing content.

    engagement orders by the stored score, which is not time-decayed -- an
    old post with a large score outranks a strong new one. Narrow the range
    to compare like with like."""
    return await StatsService(db).top_posts(
        staff, metric.value, college_id, range.value, limit
    )


@router.get("/stats/top_users", response_model=list[TopUser])
async def get_top_users(
    metric: TopUserMetric = TopUserMetric.posts,
    range: StatsRange = StatsRange.d30,
    limit: int = Query(10, ge=1, le=50),
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Most active contributors. Both post count and XP come back whichever
    one orders the list."""
    return await StatsService(db).top_users(
        staff, metric.value, college_id, range.value, limit
    )


@router.get("/stats/colleges", response_model=list[CollegeRollup])
async def get_colleges_rollup(
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """One row per college: members, posts and queue depth.

    Uses the college domain's own counts, so this and the Manage-Colleges
    table can never disagree."""
    return await StatsService(db).colleges_rollup(staff)


@router.get("/activity", response_model=list[ActivityEntry])
async def get_activity(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    college_id: UUID | None = None,
    staff: Actor = Depends(get_stats_actor),
    db: AsyncSession = Depends(get_db),
):
    """Recent staff actions, newest first.

    Post decisions only for now -- role changes and college edits join this
    once there is a general activity log. Scoped by the college of the post
    acted on, so an admin working on another campus appears in that campus's
    feed."""
    return await StatsService(db).activity(staff, college_id, limit, offset)
