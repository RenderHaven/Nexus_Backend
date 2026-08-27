from typing import Generic, TypeVar
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class Paginated(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None

class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str

class College(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    about: str | None = None
    created_at: datetime | None = None
