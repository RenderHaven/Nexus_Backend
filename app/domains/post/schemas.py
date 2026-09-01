from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from app.config import settings
from app.db.models import PostType, PostStatus, ModerationStatus, ActionStatus, MediaType,CollaborationRequestStatus
from app.domains.pool.schemas import PoolMember, PoolObject
from app.domains.user.schemas import UserBasic
from app.schemas.common import Category, College

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


class PostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    category_id: UUID
    like_count: int
    engagement_score: float
    is_active: bool

class ModerationUpdate(BaseModel):
    moderation_status: ModerationStatus


class PostIdPayload(BaseModel):
    post_id: UUID
