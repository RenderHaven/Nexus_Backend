from enum import Enum
from uuid import UUID
from pydantic import BaseModel
from app.db.models.enums import CollaborationRequestStatus

class CollabStatusUpdate(BaseModel):
    status: CollaborationRequestStatus

class CollabStatusResult(BaseModel):
    status: str
    collab_status: CollaborationRequestStatus
    post_id: UUID
    user_id: UUID
