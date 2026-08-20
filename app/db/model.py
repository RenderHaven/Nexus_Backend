import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =========================
# Enums
# =========================

class UserRole(str, enum.Enum):
    admin = "admin"
    moderator = "moderator"
    success_coach = "success_coach"
    student = "student"
    alumni = "alumni"
    guest = "guest"


class IdentityLevel(str, enum.Enum):
    spark = "spark"
    kindler = "kindler"
    amplifier = "amplifier"
    pathfinder = "pathfinder"
    horizon = "horizon"
    constellation = "constellation"


class PostType(str, enum.Enum):
    achievement = "achievement"
    knowledge = "knowledge"
    collaboration = "collaboration"
    event = "event"
    opportunity = "opportunity"
    spark = "spark"


class PostStatus(str, enum.Enum):
    published = "published"
    archived = "archived"
    deleted = "deleted"


class ModerationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    hold = "hold"
    removed = "removed"


class ModerationAction(str, enum.Enum):
    approve = "approve"
    hold = "hold"
    remove = "remove"


class ReactionType(str, enum.Enum):
    inspired = "inspired"
    curious = "curious"
    want_to_try = "want_to_try"


class MediaType(str, enum.Enum):
    image = "image"
    video = "video"
    gif = "gif"


class CollaborationStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class CollaborationResponseStatus(str, enum.Enum):
    interested = "interested"
    accepted = "accepted"
    rejected = "rejected"


class ConversationStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class MessageType(str, enum.Enum):
    text = "text"
    link = "link"
    file = "file"


class OpportunityType(str, enum.Enum):
    internship = "internship"
    competition = "competition"
    research = "research"
    fellowship = "fellowship"
    scholarship = "scholarship"


# Legacy InteractionType for backward compatibility
class InteractionType(str, enum.Enum):
    like = "like"
    comment = "comment"
    view = "view"
    share = "share"


# =========================
# Models
# =========================

class College(Base):
    __tablename__ = "colleges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    about = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="college")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(Text, nullable=False)
    role = Column(Enum(UserRole, name="user_role"), nullable=False, server_default=UserRole.student.value, default=UserRole.student)
    course = Column(String(100), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    about = Column(Text, nullable=True)
    goals = Column(Text, nullable=True)
    total_xp = Column(Integer, nullable=False, server_default="0", default=0)
    current_level = Column(Enum(IdentityLevel, name="identity_level"), nullable=False, server_default=IdentityLevel.spark.value, default=IdentityLevel.spark)
    is_alumni = Column(Boolean, nullable=False, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    college = relationship("College", back_populates="users")
    alumni_profile = relationship("AlumniProfile", uselist=False, back_populates="user")
    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
    open_to = relationship("UserOpenTo", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", foreign_keys="[Post.user_id]", back_populates="author")
    reviewed_posts = relationship("Post", foreign_keys="[Post.reviewed_by]", back_populates="reviewer")
    reactions = relationship("PostReaction", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")


class AlumniProfile(Base):
    __tablename__ = "alumni_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    graduation_year = Column(Integer, nullable=False)
    industry = Column(String(100), nullable=True)
    current_role = Column(String(100), nullable=True)
    current_company = Column(String(100), nullable=True)
    open_to_mentoring = Column(Boolean, nullable=False, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="alumni_profile")


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    posts = relationship("Post", back_populates="category")


class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="interests")
    category = relationship("Category")


class UserOpenTo(Base):
    __tablename__ = "user_open_to"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    label = Column(String(100), nullable=False)

    user = relationship("User", back_populates="open_to")


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True)
    type = Column(Enum(PostType, name="post_type"), nullable=False)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    status = Column(Enum(PostStatus, name="post_status"), nullable=False, server_default=PostStatus.published.value, default=PostStatus.published, index=True)
    moderation_status = Column(Enum(ModerationStatus, name="moderation_status"), nullable=False, server_default=ModerationStatus.pending.value, default=ModerationStatus.pending)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    like_count = Column(Integer, nullable=False, server_default="0", default=0)
    comment_count = Column(Integer, nullable=False, server_default="0", default=0)
    save_count = Column(Integer, nullable=False, server_default="0", default=0)
    engagement_score = Column(Float, nullable=False, server_default="0.0", default=0.0, index=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    author = relationship("User", foreign_keys=[user_id], back_populates="posts")
    college = relationship("College")
    category = relationship("Category", back_populates="posts")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="reviewed_posts")
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")
    achievement_details = relationship("AchievementDetail", uselist=False, back_populates="post", cascade="all, delete-orphan")
    knowledge_details = relationship("KnowledgeDetail", uselist=False, back_populates="post", cascade="all, delete-orphan")
    knowledge_saves = relationship("KnowledgeSave", back_populates="post", cascade="all, delete-orphan")
    collaboration_details = relationship("CollaborationDetail", uselist=False, back_populates="post", cascade="all, delete-orphan")
    collaboration_responses = relationship("CollaborationResponse", back_populates="post", cascade="all, delete-orphan")
    event_details = relationship("EventDetail", uselist=False, back_populates="post", cascade="all, delete-orphan")
    event_attendees = relationship("EventAttendee", back_populates="post", cascade="all, delete-orphan")
    opportunity_details = relationship("OpportunityDetail", uselist=False, back_populates="post", cascade="all, delete-orphan")
    opportunity_clicks = relationship("OpportunityClick", back_populates="post", cascade="all, delete-orphan")
    reactions = relationship("PostReaction", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")
    moderation_logs = relationship("ModerationLog", back_populates="post", cascade="all, delete-orphan")
    chat_room = relationship("ChatRoom", uselist=False, back_populates="post", cascade="all, delete-orphan")


class PostMedia(Base):
    __tablename__ = "post_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    media_type = Column(Enum(MediaType, name="media_type"), nullable=False)
    position = Column(Integer, nullable=False, server_default="1", default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="media")


class AchievementDetail(Base):
    __tablename__ = "achievement_details"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True)
    story = Column(Text, nullable=False)
    struggle = Column(Text, nullable=False)
    lesson = Column(Text, nullable=True)
    resources = Column(Text, nullable=True)
    open_to_collaborate = Column(Boolean, nullable=False, server_default="false", default=False)

    post = relationship("Post", back_populates="achievement_details")


class KnowledgeDetail(Base):
    __tablename__ = "knowledge_details"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True)
    hook = Column(Text, nullable=False)
    substance = Column(Text, nullable=False)
    resources = Column(Text, nullable=True)

    post = relationship("Post", back_populates="knowledge_details")


class KnowledgeSave(Base):
    __tablename__ = "knowledge_saves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="knowledge_saves")
    user = relationship("User")


class CollaborationDetail(Base):
    __tablename__ = "collaboration_details"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True)
    looking_for = Column(Text, nullable=False)
    status = Column(Enum(CollaborationStatus, name="collaboration_status"), nullable=False, server_default=CollaborationStatus.open.value, default=CollaborationStatus.open)

    post = relationship("Post", back_populates="collaboration_details")


class CollaborationResponse(Base):
    __tablename__ = "collaboration_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CollaborationResponseStatus, name="collaboration_response_status"), nullable=False, server_default=CollaborationResponseStatus.interested.value, default=CollaborationResponseStatus.interested)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="collaboration_responses")
    user = relationship("User")


class EventDetail(Base):
    __tablename__ = "event_details"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True)
    event_date = Column(DateTime(timezone=True), nullable=False)
    open_to_all = Column(Boolean, nullable=False, server_default="true", default=True)
    restricted_to_college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=True)
    registration_url = Column(Text, nullable=True)

    post = relationship("Post", back_populates="event_details")
    restricted_college = relationship("College")


class EventAttendee(Base):
    __tablename__ = "event_attendees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    attended_at = Column(DateTime(timezone=True), nullable=True)

    post = relationship("Post", back_populates="event_attendees")
    user = relationship("User")


class OpportunityDetail(Base):
    __tablename__ = "opportunity_details"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True)
    organisation = Column(String(255), nullable=False)
    opportunity_type = Column(Enum(OpportunityType, name="opportunity_type"), nullable=False)
    eligibility = Column(Text, nullable=True)
    any_branch_welcome = Column(Boolean, nullable=False, server_default="true", default=True)
    deadline = Column(Date, nullable=False)
    external_url = Column(Text, nullable=False)
    posted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    post = relationship("Post", back_populates="opportunity_details")
    poster = relationship("User", foreign_keys=[posted_by])


class OpportunityClick(Base):
    __tablename__ = "opportunity_clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="opportunity_clicks")
    user = relationship("User")


class PostReaction(Base):
    __tablename__ = "post_reactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(Enum(ReactionType, name="reaction_type"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="reactions")
    user = relationship("User", back_populates="reactions")


class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("post_comments.id"), nullable=True)
    is_edited = Column(Boolean, nullable=False, server_default="false", default=False)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("PostComment", remote_side=[id], backref="replies")
    edit_logs = relationship("CommentEditLog", back_populates="comment", cascade="all, delete-orphan")


class CommentEditLog(Base):
    __tablename__ = "comment_edit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("post_comments.id"), nullable=False)
    previous_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    comment = relationship("PostComment", back_populates="edit_logs")


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    coach_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(Enum(ModerationAction, name="moderation_action"), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="moderation_logs")
    coach = relationship("User")


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    status = Column(Enum(ConversationStatus, name="conversation_status"), nullable=False, server_default=ConversationStatus.active.value, default=ConversationStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="chat_room")
    participants = relationship("ChatParticipant", back_populates="chat_room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat_room", cascade="all, delete-orphan")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    collaboration_response_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_responses.id"), nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat_room = relationship("ChatRoom", back_populates="participants")
    user = relationship("User")
    collaboration_response = relationship("CollaborationResponse")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=True)
    type = Column(Enum(MessageType, name="message_type"), nullable=False, server_default=MessageType.text.value, default=MessageType.text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")


class SupportConversation(Base):
    __tablename__ = "support_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    coach_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student = relationship("User", foreign_keys=[student_id])
    coach = relationship("User", foreign_keys=[coach_id])
    messages = relationship("SupportMessage", back_populates="support_conversation", cascade="all, delete-orphan")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    support_conversation_id = Column(UUID(as_uuid=True), ForeignKey("support_conversations.id"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    support_conversation = relationship("SupportConversation", back_populates="messages")
    sender = relationship("User")


class Badge(Base):
    __tablename__ = "badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    user_badges = relationship("UserBadge", back_populates="badge")


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")


class CampusAmbassador(Base):
    __tablename__ = "campus_ambassadors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    reason_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    college = relationship("College")


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    xp_awarded = Column(Integer, nullable=False, server_default="0", default=0)
    meta_data = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False)

    user = relationship("User")
    college = relationship("College")
    category = relationship("Category")


class UserCategoryProbability(Base):
    __tablename__ = "user_category_probability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    probability = Column(Float, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    category = relationship("Category")


class CollegeCategoryProbability(Base):
    __tablename__ = "college_category_probability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    probability = Column(Float, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    college = relationship("College")
    category = relationship("Category")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, nullable=False, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")


# Compatibility alias for legacy code
PostInteraction = PostReaction