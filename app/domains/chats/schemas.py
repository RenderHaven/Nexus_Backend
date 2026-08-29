from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ConversationStatus, MessageType
from app.domains.pool.schemas import PoolMember, PoolObject


class ChatRoomSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    name: str | None = None
    status: ConversationStatus
    created_at: datetime


class ChatParticipantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_room_id: UUID
    user_id: UUID
    collaboration_response_id: UUID
    last_read_at: datetime | None = None
    joined_at: datetime


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_room_id: UUID
    sender_id: UUID
    body: str | None = None
    type: MessageType
    created_at: datetime


class SendMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)
    type: MessageType = MessageType.text


class MessagePoolObject(PoolObject):
    chat_room_id: UUID
    sender_id: UUID
    body: str | None = None
    type: MessageType
    created_at: datetime


class MessagePoolMember(PoolMember):
    chat_room_id: UUID
    sender_id: UUID
    body: str | None = None
    type: MessageType
    created_at: datetime
