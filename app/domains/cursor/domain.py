from pydantic import BaseModel
from typing import Dict, Any
from uuid import UUID

class PoolCursor(BaseModel):
    cursor_key: str
    user_id: UUID | None
    offsets: dict[str, int]

class PoolGroupCursor(BaseModel):
    cursor_key: str
    user_id: UUID | None
    offsets: dict[str, int] 