from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PoolMember(BaseModel):
    id: UUID
    name: str | None = None
    type: str
    created_at: datetime

class ZSetCursor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score:float
    member:str
