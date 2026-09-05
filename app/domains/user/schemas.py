from datetime import datetime
from uuid import UUID

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


# ----------------------------------------------------------------------
# Admin surface
#
# Everything below is staff-only. The public User schema deliberately never
# carries an email; the admin table needs one, so it gets its own row shape
# rather than widening what every reader can see.
# ----------------------------------------------------------------------

class UserSort(StrEnum):
    created_at = "created_at"
    username = "username"
    role = "role"
    total_xp = "total_xp"


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class UserAdminRow(UserBasic):
    """One row of the Manage-Users table. Staff only -- it carries email."""

    model_config = ConfigDict(from_attributes=True)

    email: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserUpdate(BaseModel):
    """
    What staff may change about someone else's account.

    Every field is optional; only what is sent is touched. Password is absent
    on purpose -- it is reset through its own endpoint, never edited inline.
    """

    role: UserRole | None = None
    college_id: UUID | None = None
    is_alumni: bool | None = None


class UserListFilters(BaseModel):
    """
    The admin table's filters, taken as a query-param model.

    college_id is what the caller asked for and is never trusted: the service
    runs it through Actor.scope_college, which substitutes the caller's own
    college unless they are an admin.
    """

    college_id: UUID | None = None
    role: UserRole | None = None
    is_alumni: bool | None = None
    is_active: bool | None = None
    q: str | None = Field(default=None, max_length=settings.MAX_USERNAME_LENGTH)
    sort: UserSort = UserSort.created_at
    order: SortOrder = SortOrder.desc


class BulkUserActionType(StrEnum):
    assign_role = "assign_role"
    deactivate = "deactivate"
    activate = "activate"


class BulkUserAction(BaseModel):
    user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=settings.MAX_BATCH_SIZE,
    )
    action: BulkUserActionType
    value: UserRole | None = Field(
        default=None,
        description="The role to assign. Required for assign_role only.",
    )

    @model_validator(mode="after")
    def _role_required_for_assign(self) -> "BulkUserAction":
        if self.action is BulkUserActionType.assign_role and self.value is None:
            raise ValueError("value is required when action is assign_role")
        return self


class BulkUserFailure(BaseModel):
    user_id: UUID
    reason: str


class BulkUserResult(BaseModel):
    """One refused id does not sink the batch."""

    updated: list[UUID] = Field(default_factory=list)
    failed: list[BulkUserFailure] = Field(default_factory=list)


class TempPasswordPayload(BaseModel):
    """
    Returned once, and never stored anywhere readable.

    There is no mail delivery yet, so the admin reads the temporary password
    off the response and passes it on themselves.
    """

    user_id: UUID
    temp_password: str


class MyPermissions(BaseModel):
    """
    What this account may do, straight from app/rules.

    The frontend hides sections from this rather than guessing from the role
    name, so adding a permission to the rules table is all it takes to change
    what the UI offers.
    """

    user_id: UUID
    role: UserRole
    college_id: UUID | None = None
    is_platform_wide: bool = False
    permissions: list[str] = Field(default_factory=list)


class User(UserBasic):
    """
    A full profile. Email is deliberately absent: it is never returned by any
    endpoint, including /users/me.
    """

    profile: UserProfile = Field(default_factory=UserProfile)
    created_at: datetime | None = None
