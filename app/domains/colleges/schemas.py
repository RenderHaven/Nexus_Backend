from uuid import UUID

from pydantic import BaseModel, Field

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
