from typing import Generic, TypeVar
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class Paginated(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


class Page(BaseModel, Generic[T]):
    """
    An offset page of a table.

    Sits alongside Paginated, which is the cursor shape used by the pools. A
    cursor is right for an endless feed; an admin table needs to jump to page
    seven, so it pages by offset instead.

    total is the size of this page, not of the whole filtered set -- counting
    the set would cost a second query on every keystroke of a filter. The real
    per-status totals come from the counts endpoint, which is one grouped
    count rather than one count per tab.
    """

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def of(cls, items: list[T], limit: int, offset: int) -> "Page[T]":
        return cls(items=items, total=len(items), limit=limit, offset=offset)

class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str

class College(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    tagline: str | None = None
    location: str | None = None
    about: str | None = None
    created_at: datetime | None = None
