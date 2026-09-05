from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import UserRole
from app.schemas.common import College as CollegeBasic


class CollegeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tagline: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    about: str | None = Field(default=None, max_length=2000)


class CollegeUpdate(BaseModel):
    """Only the fields present in the payload are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    tagline: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    about: str | None = Field(default=None, max_length=2000)


class CollegeIdPayload(BaseModel):
    college_id: UUID


# ----------------------------------------------------------------------
# Admin surface
#
# The counts live here rather than on CollegeBasic: that schema is embedded
# in every post and user response, and widening it would put three extra
# aggregates on payloads that never asked for them.
# ----------------------------------------------------------------------

class CollegeSort(StrEnum):
    name = "name"
    created_at = "created_at"


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class CollegeAdminRow(CollegeBasic):
    """One row of the Manage-Colleges table."""

    model_config = ConfigDict(from_attributes=True)

    user_count: int = 0
    post_count: int = 0
    pending_count: int = 0


class CollegeStats(BaseModel):
    """
    The detail drawer's numbers.

    active_this_week counts people who posted, because there is no last-seen
    signal yet -- it undercounts anyone who only reads.
    """

    users: int = 0
    posts: int = 0
    pending: int = 0
    active_this_week: int = 0


class CollegeListFilters(BaseModel):
    """
    Taken as a query-param model via Depends() -- the
    Annotated[..., Query()] form stops flattening into individual parameters
    as soon as another query parameter sits beside it.
    """

    q: str | None = Field(default=None, max_length=255)
    sort: CollegeSort = CollegeSort.name
    order: SortOrder = SortOrder.asc


class CollegePeopleFilters(BaseModel):
    """Filters for one campus's People tab."""

    role: UserRole | None = None
    is_alumni: bool | None = None
    q: str | None = Field(default=None, max_length=100)
