from typing import Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field,AliasChoices
from app.db.models import PostType, PostStatus, ModerationStatus, ActionStatus, MediaType
from app.domains.pool.schemas import PoolMember, PoolObject
from app.domains.user.schemas import Author
from app.schemas.common import Category, College

class PostResource(BaseModel):
    title: str
    link: str

class PostMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    url: str
    media_type: MediaType
    position: int

class PostBase(BaseModel):
    category_id: UUID
    type: PostType = PostType.spark
    title: str | None = None
    content: str
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | list[dict[str, Any]] | None = None
    action_status: ActionStatus | None = None

class PostPoolObject(PoolObject):
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
    media_ids: list[str] = Field(default_factory=list)

class PostUpdate(BaseModel):
    category_id: UUID | None = None
    type: PostType | None = None
    title: str | None = None
    content: str | None = None
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | list[dict[str, Any]] | None = None
    action_status: ActionStatus | None = None
    status: PostStatus | None = None
    moderation_status: ModerationStatus | None = None
    is_active: bool | None = None
    media_ids: list[str] | None = None

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
    author: Author | None = None
    category: Category | None = None
    college: College | None = None
    media: list[PostMedia] = Field(default_factory=list)
    is_liked: bool | None = None

class PostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    category_id: UUID
    like_count: int
    engagement_score: float
    is_active: bool

class PostIdResponse(BaseModel):
    post_id: UUID
    status: str | None = None
    message: str | None = None
