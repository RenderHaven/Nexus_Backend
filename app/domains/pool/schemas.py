from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field ,AliasChoices


class PoolMember(BaseModel):
    id: UUID
    name: str | None = None
    type: str
    created_at: datetime

class ZSetCursor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score:float
    member:str

class PoolObject(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str | None = Field(default=None, validation_alias=AliasChoices("name", "title"))