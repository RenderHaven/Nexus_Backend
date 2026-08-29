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
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base
from .enums import (
    PostType,
    PostStatus,
    ActionStatus,
    ModerationStatus,
    ModerationAction,
    MediaType,
    CollaborationResponseStatus,
)

class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True)
    type = Column(Enum(PostType, name="post_type"), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)

    # 4 extra nullable columns shared across types
    date_at = Column(DateTime(timezone=True), nullable=True)
    restricted_to_college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=True)
    resources = Column(JSONB, nullable=True)
    action_status = Column(Enum(ActionStatus, name="action_status"), nullable=True)

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
    college = relationship("College", foreign_keys=[college_id])
    category = relationship("Category", back_populates="posts")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="reviewed_posts")
    restricted_college = relationship("College", foreign_keys=[restricted_to_college_id])
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")
    collaboration_responses = relationship("CollaborationResponse", back_populates="post", cascade="all, delete-orphan")
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


class CollaborationResponse(Base):
    __tablename__ = "collaboration_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CollaborationResponseStatus, name="collaboration_response_status"), nullable=False, server_default=CollaborationResponseStatus.interested.value, default=CollaborationResponseStatus.interested)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    user_note = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)
    post = relationship("Post", back_populates="collaboration_responses")
    user = relationship("User")
