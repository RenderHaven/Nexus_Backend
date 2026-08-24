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


class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # NULL = top-level comment; otherwise this is a reply.
    parent_id = Column(UUID(as_uuid=True), ForeignKey("post_comments.id"), nullable=True)

    body = Column(Text, nullable=False)

    # Denormalized counter for fast reads.
    reply_count = Column(Integer, nullable=False, server_default="0", default=0)

    is_edited = Column(Boolean, nullable=False, server_default="false", default=False)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")

    parent = relationship(
        "PostComment",
        remote_side=[id],
        back_populates="replies",
    )

    replies = relationship(
        "PostComment",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    edit_logs = relationship(
        "CommentEditLog",
        back_populates="comment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Root comments of a post, optimized for cursor pagination.
        Index(
            "idx_comments_post_root_cursor",
            "post_id",
            "created_at",
            "id",
            postgresql_where=(
                (parent_id.is_(None)) &
                (is_active.is_(True))
            ),
        ),

        # Replies of a comment, optimized for cursor pagination.
        Index(
            "idx_comments_parent_cursor",
            "parent_id",
            "created_at",
            "id",
            postgresql_where=is_active.is_(True),
        ),
    )


class CommentEditLog(Base):
    __tablename__ = "comment_edit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("post_comments.id"), nullable=False)
    previous_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    comment = relationship("PostComment", back_populates="edit_logs")
