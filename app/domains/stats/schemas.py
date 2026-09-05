"""
Shapes for the admin dashboard.

Every number here is counted live off posts, users and moderation_logs. There
is no rollup table yet, so a wide range over a large platform is a real
aggregate query -- see ADMIN_API_PLAN.md phase 2.3 for what replaces this
when it stops being cheap.
"""
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ModerationAction, PostType, UserRole


class StatsRange(StrEnum):
    """How far back to look."""

    d7 = "7d"
    d30 = "30d"
    d90 = "90d"
    y1 = "1y"
    all = "all"


class Interval(StrEnum):
    day = "day"
    week = "week"
    month = "month"


class BreakdownBy(StrEnum):
    type = "type"
    category = "category"
    college = "college"


class TopPostMetric(StrEnum):
    engagement = "engagement"
    likes = "likes"
    comments = "comments"


class TopUserMetric(StrEnum):
    posts = "posts"
    xp = "xp"


# ----------------------------------------------------------------------
# Payloads
# ----------------------------------------------------------------------

class Overview(BaseModel):
    """The headline counters across the top of the dashboard."""

    users: int = 0
    colleges: int = 0
    posts: int = 0
    pending: int = 0
    active_today: int = 0


class PostsBucket(BaseModel):
    bucket: date
    created: int = 0
    approved: int = 0
    removed: int = 0


class UsersBucket(BaseModel):
    bucket: date
    signups: int = 0
    by_role: dict[str, int] = Field(default_factory=dict)


class ModeratorThroughput(BaseModel):
    moderator_id: UUID
    username: str | None = None
    decisions: int = 0


class ModerationStats(BaseModel):
    """
    Queue health.

    median_minutes_to_decision is measured from a post's creation to its
    review, over posts actually decided in the range -- posts still waiting
    have no decision time and are counted in `pending` instead.

    by_moderator comes from moderation_logs, which only started being written
    when the audit trail was implemented; it has no history before that.
    """

    pending: int = 0
    approved: int = 0
    hold: int = 0
    removed: int = 0
    median_minutes_to_decision: float | None = None
    by_moderator: list[ModeratorThroughput] = Field(default_factory=list)


class BreakdownSlice(BaseModel):
    key: str
    label: str | None = None
    count: int = 0


class TopPost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    type: PostType
    college_id: UUID | None = None
    user_id: UUID
    like_count: int = 0
    comment_count: int = 0
    engagement_score: float = 0.0
    created_at: datetime


class TopUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    college_id: UUID | None = None
    role: UserRole
    total_xp: int = 0
    post_count: int = 0


class CollegeRollup(BaseModel):
    college_id: UUID
    name: str
    users: int = 0
    posts: int = 0
    pending: int = 0


class ActivityEntry(BaseModel):
    """
    One staff action.

    Sourced from moderation_logs, so today this is post decisions only. Role
    changes and college edits join it when a general activity log exists
    (ADMIN_API_PLAN.md phase 2.1).
    """

    id: UUID
    action: ModerationAction
    post_id: UUID
    college_id: UUID | None = None
    moderator_id: UUID
    moderator_username: str | None = None
    note: str | None = None
    created_at: datetime
