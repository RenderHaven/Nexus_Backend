import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ============================
# ENUMS
# ============================

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


# ============================
# MODELS
# ============================

class College(Base):
    __tablename__ = "colleges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), nullable=False)
    about = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    users = relationship("User", back_populates="college")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id"),
        nullable=False,
        index=True,
    )

    username = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(Text, nullable=False)

    role = Column(
        Enum(UserRole),
        nullable=False,
        server_default="student",
    )

    about = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    college = relationship("College", back_populates="users")
    posts = relationship("Post", back_populates="author")
    interactions = relationship("PostInteraction", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(100), unique=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    posts = relationship("Post", back_populates="category")


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String(255))
    body = Column(Text)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(PostStatus),
        nullable=False,
        server_default="published",
        index=True,
    )

    engagement_score = Column(
        Integer,
        nullable=False,
        server_default="0",
        index=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )

    # updated_at = Column(
    #     DateTime(timezone=True),
    #     server_default=text("CURRENT_TIMESTAMP"),
    #     onupdate=text("CURRENT_TIMESTAMP"),
    # )

    author = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    media = relationship(
        "PostMedia",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    interactions = relationship(
        "PostInteraction",
        back_populates="post",
        cascade="all, delete-orphan",
    )


class PostMedia(Base):
    __tablename__ = "post_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id"),
        nullable=False,
        index=True,
    )

    url = Column(Text, nullable=False)

    media_type = Column(
        Enum(MediaType),
        nullable=False,
    )

    position = Column(
        Integer,
        nullable=False,
        server_default="1",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    post = relationship("Post", back_populates="media")


class PostInteraction(Base):
    __tablename__ = "post_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    interaction_type = Column(
        Enum(InteractionType),
        nullable=False,
    )

    body = Column(Text)

    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("post_interactions.id"),
    )

    is_edited = Column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )

    post = relationship("Post", back_populates="interactions")
    user = relationship("User", back_populates="interactions")

    parent = relationship(
        "PostInteraction",
        remote_side=[id],
        backref="replies",
    )

    logs = relationship(
        "PostInteractionLog",
        back_populates="interaction",
        cascade="all, delete-orphan",
    )


class PostInteractionLog(Base):
    __tablename__ = "post_interaction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    post_interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("post_interactions.id"),
        nullable=False,
        index=True,
    )

    log_type = Column(
        Enum(InteractionLogType),
        nullable=False,
    )

    body = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    interaction = relationship(
        "PostInteraction",
        back_populates="logs",
    )