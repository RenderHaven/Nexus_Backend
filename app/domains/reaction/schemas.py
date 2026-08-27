from enum import Enum
from uuid import UUID
from pydantic import BaseModel

class ReactionAction(str, Enum):
    liked = "like.created"
    unliked = "like.deleted"

class ReactionResult(BaseModel):
    status: str
    action: ReactionAction
    post_id: UUID
    user_id: UUID
