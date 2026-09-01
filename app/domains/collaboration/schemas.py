from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import CollaborationRequestStatus
from app.domains.user.schemas import UserMini


class CollabStatusUpdate(BaseModel):
    status: CollaborationRequestStatus


class CollabRequestCreate(BaseModel):
    """
    sender_id must be the authenticated user. It is required so the client
    states plainly who it believes it is acting as, and the server refuses
    the request if that does not match the token.
    """

    sender_id: UUID
    note: str | None = Field(default=None, max_length=1000)


class CollabRevokeRequest(BaseModel):
    """sender_id must be the authenticated user, as with sending."""

    sender_id: UUID


class CollabReviewRequest(BaseModel):
    """The post author's decision on one request."""

    accept: bool
    note: str | None = Field(default=None, max_length=1000)


class CollabStatusResult(BaseModel):
    status: str
    collab_status: CollaborationRequestStatus
    request_id: UUID | None = None
    post_id: UUID
    sender_id: UUID
    recipient_id: UUID | None = None


class CollabRequest(BaseModel):
    """
    One join request, from either side.

    sender is who asked; recipient is the post author who decides.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    sender_id: UUID
    recipient_id: UUID
    status: CollaborationRequestStatus
    user_note: str | None = None
    admin_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    sender: UserMini | None = None
    recipient: UserMini | None = None
