from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domains.user.schemas import UserMini


class Comment(BaseModel):
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
    # Resolved from user_id at read time, never stored in comment:{id} --
    # otherwise a rename would have to chase every cached comment.
    author: UserMini | None = None


class CommentRequest(BaseModel):
    comment: str = Field(..., max_length=1000)
