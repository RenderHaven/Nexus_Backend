
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime,
    ForeignKey, Enum, text
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    admin = "admin"
    moderator = "moderator"
    success_coach = "success_coach"
    student = "student"
    guest = "guest"

class PostStatus(enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"
    deleted = "deleted"

class InteractionType(enum.Enum):
    like = "like"
    comment = "comment"
    share = "share"

class MediaType(enum.Enum):
    image = "image"
    video = "video"
    gif = "gif"

class InteractionLogType(enum.Enum):
    created = "created"
    edited = "edited"

class College(Base):
    __tablename__ = "colleges"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    about = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(Text, nullable=False)
    role = Column(Enum(UserRole), nullable=False, server_default="student")
    about = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class Category(Base):
    __tablename__ = "categories"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class Post(Base):
    __tablename__ = "posts"
    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String)
    body = Column(Text)
    media_urls = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    status = Column(Enum(PostStatus), server_default="published")
    engagement_score = Column(Integer, server_default="0")
    is_active = Column(Boolean, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class PostMedia(Base):
    __tablename__ = "post_media"
    id = Column(UUID(as_uuid=True), primary_key=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    url = Column(Text, nullable=False)
    media_type = Column(Enum(MediaType), nullable=False)
    position = Column(Integer, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class PostInteraction(Base):
    __tablename__ = "post_interactions"
    id = Column(UUID(as_uuid=True), primary_key=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(Enum(InteractionType), nullable=False)
    body = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("post_interactions.id"))
    is_edited = Column(Boolean, server_default=text("false"))
    is_active = Column(Boolean, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class PostInteractionLog(Base):
    __tablename__ = "post_intrections_logs"
    id = Column(UUID(as_uuid=True), primary_key=True)
    post_intreaction_id = Column(UUID(as_uuid=True), ForeignKey("post_interactions.id"), nullable=False)
    type = Column(Enum(InteractionLogType), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
