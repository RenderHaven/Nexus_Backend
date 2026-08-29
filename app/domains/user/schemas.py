from typing import Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import UserRole, IdentityLevel
from app.domains.pool.schemas import PoolMember, PoolObject

class UserMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str

class UserBasic(UserMini):
    email: str | None = None
    college_id: UUID | None = None
    role: UserRole

class UserPoolObject(PoolObject):
    id:UUID
    college_id:UUID
    created_at: datetime | None = None
    name:str

class UserPoolMember(PoolMember):
    id:UUID
    college_id:UUID
    name:str

class Author(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    college_id: UUID | None = None
    username: str
    role: UserRole = UserRole.student

class User(UserBasic):
    total_xp: int = 0
    current_level: IdentityLevel = IdentityLevel.spark
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
