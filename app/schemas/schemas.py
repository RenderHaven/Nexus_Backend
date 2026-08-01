from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.model import MediaType


class PostMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    media_type: MediaType
    position: int


class UserMiniResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str


class CategoryMiniResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    body: str | None

    engagement_score: int
    # likes: int
    # comments: int
    # shares: int

    created_at: datetime

    user_id: UUID
    category_id: UUID
    media: list[PostMediaResponse]

class PoolPost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime

    engagement_score: float
    is_active: bool