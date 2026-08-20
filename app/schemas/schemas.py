from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.db.model import (
    UserRole,
    IdentityLevel,
    PostType,
    PostStatus,
    ModerationStatus,
    ReactionType,
    MediaType,
    CollaborationStatus,
    CollaborationResponseStatus,
    OpportunityType,
)


class PostMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    media_type: MediaType
    position: int


class AchievementDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: UUID
    story: str
    struggle: str
    lesson: str | None = None
    resources: str | None = None
    open_to_collaborate: bool = False


class KnowledgeDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: UUID
    hook: str
    substance: str
    resources: str | None = None


class CollaborationDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: UUID
    looking_for: str
    status: CollaborationStatus = CollaborationStatus.open


class EventDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: UUID
    event_date: datetime
    open_to_all: bool = True
    restricted_to_college_id: UUID | None = None
    registration_url: str | None = None


class OpportunityDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: UUID
    organisation: str
    opportunity_type: OpportunityType
    eligibility: str | None = None
    any_branch_welcome: bool = True
    deadline: date
    external_url: str
    posted_by: UUID


class UserMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    college_id: UUID | None = None
    username: str
    email: str | None = None
    role: UserRole = UserRole.student
    course: str | None = None
    year_of_study: int | None = None
    about: str | None = None
    goals: str | None = None
    total_xp: int = 0
    current_level: IdentityLevel = IdentityLevel.spark
    is_alumni: bool = False
    created_at: datetime | None = None

class Author(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:UUID
    college_id:UUID | None = None
    username:str
    role:UserRole=UserRole.student


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class PostSmall(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    category_id: UUID
    engagement_score: float
    is_active: bool


class Post(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    college_id: UUID | None = None
    category_id: UUID
    type: PostType = PostType.spark
    title: str | None = None
    body: str | None = None
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
    author:Author | None=None
    media: list[PostMedia] = []
    achievement_details: AchievementDetailSchema | None = None
    knowledge_details: KnowledgeDetailSchema | None = None
    collaboration_details: CollaborationDetailSchema | None = None
    event_details: EventDetailSchema | None = None
    opportunity_details: OpportunityDetailSchema | None = None

    is_liked: bool | None = None


class Feed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    posts: dict[str, dict[str, list[Post]]]
    feed_id: UUID | None = None