from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.db.models import IdentityLevel, UserRole
from app.domains.pool.schemas import PoolMember, PoolObject
from app.domains.user.profile_schemas import UserProfile


class UserMini(BaseModel):
    """The smallest useful reference to a person."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    college_id: UUID | None = None
    role: UserRole


class UserBasic(UserMini):
    is_alumni: bool = False
    total_xp: int = 0
    current_level: IdentityLevel = IdentityLevel.spark


class UserPoolObject(PoolObject):
    id: UUID
    username: str
    college_id: UUID
    role: UserRole = UserRole.student
    created_at: datetime | None = None
    is_alumni: bool = False


class UserPoolMember(PoolMember):
    id: UUID
    username: str
    college_id: UUID
    role: UserRole = UserRole.student
    is_alumni: bool = False
    created_at: datetime | None = None


class UserCreate(BaseModel):
    """What staff supply when adding someone to a college."""

    username: str = Field(..., min_length=1, max_length=settings.MAX_USERNAME_LENGTH)
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    college_id: UUID
    role: UserRole = UserRole.student
    is_alumni: bool = False


class UserIdPayload(BaseModel):
    user_id: UUID


class User(UserBasic):
    """
    A full profile. Email is deliberately absent: it is never returned by any
    endpoint, including /users/me.
    """

    profile: UserProfile = Field(default_factory=UserProfile)
    created_at: datetime | None = None
