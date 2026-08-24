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
from .enums import UserRole,IdentityLevel

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(Text, nullable=False)
    role = Column(Enum(UserRole, name="user_role"), nullable=False, server_default=UserRole.student.value, default=UserRole.student)
    is_alumni = Column(Boolean, nullable=False, server_default="false", default=False)
    total_xp = Column(Integer, nullable=False, server_default="0", default=0)
    current_level = Column(Enum(IdentityLevel, name="identity_level"), nullable=False, server_default=IdentityLevel.spark.value, default=IdentityLevel.spark)
    profile = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    college = relationship("College", back_populates="users")
    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
    open_to = relationship("UserOpenTo", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", foreign_keys="[Post.user_id]", back_populates="author")
    reviewed_posts = relationship("Post", foreign_keys="[Post.reviewed_by]", back_populates="reviewer")
    reactions = relationship("PostReaction", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")


class UserInterest(Base):
    __tablename__ = "user_interests"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_interests_user_category"),
    )

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
