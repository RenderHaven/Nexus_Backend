from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.post.schemas import PostBasic
from app.domains.user.schemas import UserBasic
from app.schemas.common import College


class SearchScope(StrEnum):
    """Which kinds of thing a search should look through."""

    all = "all"
    posts = "posts"
    users = "users"
    colleges = "colleges"


class SearchResult(BaseModel):
    """
    One search response.

    Every bucket is always present, so a client can render its sections
    without checking which ones came back.
    """

    query: str
    posts: list[PostBasic] = Field(default_factory=list)
    users: list[UserBasic] = Field(default_factory=list)
    colleges: list[College] = Field(default_factory=list)
