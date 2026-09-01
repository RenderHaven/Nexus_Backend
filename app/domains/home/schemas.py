from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrendingTopic(BaseModel):
    """A subject a lot of people are posting about right now."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    post_count: int = 0
    category_id: UUID | None = None


class NewsItem(BaseModel):
    """An announcement shown on a college's home screen."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str | None = None
    link: str | None = None
    image_url: str | None = None
    college_id: UUID | None = None
    published_at: datetime | None = None


class Banner(BaseModel):
    """A campus banner across the top of the home screen."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    image_url: str | None = None
    link: str | None = None
    college_id: UUID | None = None
