from datetime import date

from pydantic import BaseModel, Field

from app.config import settings

class SocialLink(BaseModel):
    title: str
    link: str

class Experience(BaseModel):
    title: str
    organisation: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False

class Education(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None

class Project(BaseModel):
    title: str
    description: str | None = None
    link: str | None = None
    tech_stack: list[str] | None = None

class JourneyMilestone(BaseModel):
    title: str
    description: str | None = None
    date: date
    icon: str | None = None

class UserProfile(BaseModel):
    """
    A user's profile. Every field is optional, and a partial payload only
    touches the fields it names — anything omitted is left as it was.
    """

    about: str | None = Field(default=None, max_length=settings.MAX_ABOUT_LENGTH)
    skills: list[str] | None = Field(default=None, max_length=settings.MAX_SKILLS)
    social_links: list[SocialLink] | None = Field(
        default=None, max_length=settings.MAX_PROFILE_ITEMS
    )

    experience: list[Experience] | None = Field(
        default=None, max_length=settings.MAX_PROFILE_ITEMS
    )
    education: list[Education] | None = Field(
        default=None, max_length=settings.MAX_PROFILE_ITEMS
    )
    projects: list[Project] | None = Field(
        default=None, max_length=settings.MAX_PROFILE_ITEMS
    )
    journey: list[JourneyMilestone] | None = Field(
        default=None, max_length=settings.MAX_PROFILE_ITEMS
    )
