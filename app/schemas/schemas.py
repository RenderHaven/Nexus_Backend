from datetime import datetime, date
from typing import Any
from uuid import UUID
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.db.models import (
    UserRole,
    IdentityLevel,
    PostType,
    PostStatus,
    ModerationStatus,
    ModerationAction,
    ReactionType,
    MediaType,
    ActionStatus,
    CollaborationResponseStatus,
    ConversationStatus,
    MessageType,
)


class PostMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    media_type: MediaType
    position: int


class StudentProfile(BaseModel):
    course: str | None = None
    year_of_study: int | None = None
    about: str | None = None
    goals: str | None = None


class AlumniProfile(BaseModel):
    course: str | None = None
    about: str | None = None
    goals: str | None = None
    graduation_year: int | None = None
    industry: str | None = None
    current_role: str | None = None
    current_company: str | None = None
    open_to_mentoring: bool = False


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
    is_alumni: bool = False
    total_xp: int = 0
    current_level: IdentityLevel = IdentityLevel.spark
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class Author(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    college_id: UUID | None = None
    username: str
    role: UserRole = UserRole.student


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class College(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    about: str | None = None
    created_at: datetime | None = None


class UserInterest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    category_id: UUID
    created_at: datetime | None = None
    category: Category | None = None


class UserOpenTo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    label: str


class PostResource(BaseModel):
    title: str
    link: str


class PostSmall(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    category_id: UUID
    like_count:UUID
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
    content: str

    # 4 extra nullable columns
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | list[dict[str, Any]] | None = None
    action_status: ActionStatus | None = None

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


class PostIdResponse(BaseModel):
    post_id: UUID
    status: str | None = None
    message: str | None = None


class PostCreate(BaseModel):
    category_id: UUID
    type: PostType
    title: str | None=None
    content: str
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | None = None
    action_status: ActionStatus | None = None
    media_ids: list[str] = Field(default_factory=list)


class PostUpdate(BaseModel):
    category_id: UUID | None = None
    type: PostType | None = None
    title: str | None = None
    content: str | None = None
    date_at: datetime | None = None
    restricted_to_college_id: UUID | None = None
    resources: list[PostResource] | None = None
    action_status: ActionStatus | None = None
    status: PostStatus | None = None
    moderation_status: ModerationStatus | None = None
    is_active: bool | None = None
    media_ids: list[str] | None = None


class CommentRequest(BaseModel):
    comment: str = Field(..., max_length=1000)


class CollaborationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    status: CollaborationResponseStatus = CollaborationResponseStatus.interested
    created_at: datetime | None = None


class EventAttendee(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    registered_at: datetime | None = None
    attended_at: datetime | None = None


class OpportunityClick(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    clicked_at: datetime | None = None


class PostReaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    type: ReactionType
    created_at: datetime | None = None


class PostComment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    body: str
    parent_id: UUID | None = None
    reply_count: int = 0
    is_edited: bool = False
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ModerationLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    coach_id: UUID
    action: ModerationAction
    note: str | None = None
    created_at: datetime | None = None


class ChatRoom(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    status: ConversationStatus = ConversationStatus.active
    created_at: datetime | None = None


class ChatParticipant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_room_id: UUID
    user_id: UUID
    collaboration_response_id: UUID
    last_read_at: datetime | None = None
    joined_at: datetime | None = None


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_room_id: UUID
    sender_id: UUID
    body: str | None = None
    type: MessageType = MessageType.text
    created_at: datetime | None = None


class ActivityLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    college_id: UUID
    action_type: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    category_id: UUID | None = None
    xp_awarded: int = 0
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "meta_data"),
    )
    created_at: datetime | None = None


class CategoryProbability(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    probability: float
    updated_at: datetime | None = None


class UserCategoryProbability(CategoryProbability):
    user_id: UUID


class CollegeCategoryProbability(CategoryProbability):
    college_id: UUID


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    is_read: bool = False
    created_at: datetime | None = None


class Feed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    posts: list[Post]
    cursor_key: str | None = None
