from datetime import datetime
from uuid import UUID
from enum import StrEnum

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from app.config import settings
from app.db.models import (
    ActionStatus,
    CollaborationRequestStatus,
    MediaType,
    ModerationAction,
    ModerationStatus,
    PostStatus,
    PostType,
)
from app.domains.pool.schemas import PoolMember, PoolObject
from app.domains.user.schemas import UserBasic
from app.schemas.common import Category, College

class ModerationSort(StrEnum):
    """Sortable columns on the moderation queue. Anything not listed here
    cannot reach the ORDER BY, so the column name is never caller-supplied."""

    created_at = "created_at"
    reviewed_at = "reviewed_at"
    engagement = "engagement"


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class PostResource(BaseModel):
    title: str
    link: str

class PostMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID
    url: str
    public_id: str | None = None
    type: MediaType = Field(
        validation_alias=AliasChoices("type", "media_type"),
        serialization_alias="type",
    )
    position: int


class PostMediaInput(BaseModel):
    public_id: str
    url: str
    type: MediaType = Field(
        validation_alias=AliasChoices("type", "media_type"),
        serialization_alias="type",
    )

class PostBase(BaseModel):
    category_id: UUID
    type: PostType = PostType.spark
    title: str | None = Field(default=None, max_length=settings.MAX_TITLE_LENGTH)
    content: str = Field(..., min_length=1, max_length=settings.MAX_BODY_LENGTH)
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | None = None
    action_status: ActionStatus | None = None

class PostPoolObject(PoolObject):
    title: str | None = Field(default=None, validation_alias=AliasChoices("name", "title"))
    type: str
    category_id: UUID | None = None
    user_id: UUID = Field(validation_alias=AliasChoices("user_id", "created_by"))

    created_at: datetime

    is_active: bool

    engagement_score: float = 0.0

class PostPoolMember(PoolMember):
    title: str | None = None
    type:PostType|None=None
    created_at: datetime
    
class PostCreate(PostBase):
    media: list[PostMediaInput] = Field(
        default_factory=list,
        max_length=settings.MAX_MEDIA_COUNT,
    )

class PostUpdate(BaseModel):
    """
    What an author may change about their own post.

    status, moderation_status and is_active are deliberately absent: status is
    changed through the archive/publish/delete actions, and the other two are
    decided by moderation.
    """

    category_id: UUID | None = None
    type: PostType | None = None
    title: str | None = Field(default=None, max_length=settings.MAX_TITLE_LENGTH)
    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=settings.MAX_BODY_LENGTH,
    )
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | None = None
    action_status: ActionStatus | None = None
    media: list[PostMediaInput] | None = Field(
        default=None,
        max_length=settings.MAX_MEDIA_COUNT,
    )

class Post(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    college_id: UUID | None = None
    status: PostStatus = PostStatus.published
    moderation_status: ModerationStatus = ModerationStatus.pending
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    like_count: int = 0
    comment_count: int = 0
    save_count: int = 0
    engagement_score: float = 0.0
    is_active: bool = True
    created_at: datetime
    author: UserBasic | None = None
    category: Category | None = None
    collab_status: CollaborationRequestStatus | None = None
    college: College | None = None
    media: list[PostMedia] = Field(default_factory=list)
    is_liked: bool | None = None

class PostBasic(BaseModel):
    """A post reduced to what a card or a search hit needs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    type: PostType
    content: str
    college_id: UUID | None = None
    category_id: UUID | None = None
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime
    author: UserBasic | None = None
    # Only filled when the caller is signed in; a card in a search result
    # shows like state the same way a feed card does.
    is_liked: bool | None = None


class PostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    category_id: UUID
    like_count: int
    engagement_score: float
    is_active: bool

# ----------------------------------------------------------------------
# Moderation
#
# A decision is always one of approved / hold / removed. pending is the state
# a post starts in and returns to when its author edits it -- it is never a
# moderator's choice, so it is not offered here.
# ----------------------------------------------------------------------

DECIDABLE_STATUSES: frozenset[ModerationStatus] = frozenset(
    {
        ModerationStatus.approved,
        ModerationStatus.hold,
        ModerationStatus.removed,
    }
)


class ModerationDecision(BaseModel):
    """A moderator's verdict, shared by the single and bulk paths."""

    moderation_status: ModerationStatus
    note: str | None = Field(
        default=None,
        max_length=settings.MAX_BODY_LENGTH,
        description="Why. Recorded in the audit trail and shown to the author.",
    )

    @field_validator("moderation_status")
    @classmethod
    def _must_be_a_decision(cls, value: ModerationStatus) -> ModerationStatus:
        if value not in DECIDABLE_STATUSES:
            allowed = ", ".join(sorted(s.value for s in DECIDABLE_STATUSES))
            raise ValueError(f"moderation_status must be one of: {allowed}")
        return value


class ModerationUpdate(ModerationDecision):
    """One post. Kept as its own name because the route already used it."""


class BulkModerationUpdate(ModerationDecision):
    post_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=settings.MAX_BATCH_SIZE,
    )


class BulkModerationFailure(BaseModel):
    post_id: UUID
    reason: str


class BulkModerationResult(BaseModel):
    """
    One bad id does not fail the batch -- the moderator gets told which rows
    went through and which did not.
    """

    updated: list[UUID] = Field(default_factory=list)
    failed: list[BulkModerationFailure] = Field(default_factory=list)


class ModerationCounts(BaseModel):
    """Tab badges. One grouped count, not four."""

    pending: int = 0
    approved: int = 0
    hold: int = 0
    removed: int = 0


class ModerationLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    action: ModerationAction
    note: str | None = None
    created_at: datetime
    moderator: UserBasic | None = Field(
        default=None,
        validation_alias=AliasChoices("moderator", "coach"),
    )


class ModerationQueueFilters(BaseModel):
    """
    Everything the queue table can narrow by.

    Declared once and taken as a query-param model so the filter list is not
    copy-pasted across the listing and count routes.

    college_id is what the caller *asked* for. It is never trusted: the
    service runs it through Actor.scope_college, which substitutes the
    caller's own college unless they are an admin.
    """

    college_id: UUID | None = None
    user_id: UUID | None = None
    category_id: UUID | None = None
    type: PostType | None = None
    q: str | None = Field(default=None, max_length=settings.MAX_TITLE_LENGTH)
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort: ModerationSort = ModerationSort.created_at
    order: SortOrder = SortOrder.asc


class PostIdPayload(BaseModel):
    post_id: UUID
