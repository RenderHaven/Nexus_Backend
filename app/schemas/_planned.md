# Planned Schemas

These schemas were extracted from the legacy `schemas.py` file. They are parked here until their respective features (chat, notifications, etc.) are implemented and they can be moved into their own domain folders (`app/domains/<new-domain>/schemas.py`).

```python
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
    CollaborationRequestStatus,
    ConversationStatus,
    MessageType,
)

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

class CollaborationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    status: CollaborationRequestStatus = CollaborationRequestStatus.interested
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
```