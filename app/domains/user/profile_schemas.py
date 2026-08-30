from datetime import date
from pydantic import BaseModel, Field

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
    about: str | None = None
    skills: list[str] | None = None
    social_links: list[SocialLink] | None = None

    experience: list[Experience] | None = None
    education: list[Education] | None = None
    projects: list[Project] | None = None
    journey: list[JourneyMilestone] | None = None
