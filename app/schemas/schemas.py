from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.model import MediaType


class PostMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    media_type: MediaType
    position: int


class UserMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:UUID
    username:str

    


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class PostSmall(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    category_id:UUID

    engagement_score: float
    is_active: bool

class Post(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    title: str | None
    body: str | None

    engagement_score: int

    created_at: datetime

    user_id: UUID
    category_id: UUID

    media: list[PostMedia]
    
    like_count: int = 0
    is_liked: bool | None = None

class Feed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    posts: dict[str, dict[str,list[Post]]]
    feed_id:UUID|None=None