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
from .enums import ConversationStatus,MessageType

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    name = Column(Text, nullable=True)
    status = Column(Enum(ConversationStatus, name="conversation_status"), nullable=False, server_default=ConversationStatus.active.value, default=ConversationStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="chat_room")
    participants = relationship("ChatParticipant", back_populates="chat_room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat_room", cascade="all, delete-orphan")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    __table_args__ = (
        UniqueConstraint("chat_room_id", "user_id", name="uq_chat_participants_room_user"),
    )

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
