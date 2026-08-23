from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PoolPost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    type: str
    category_id: UUID | None = None
    user_id: UUID = Field(validation_alias=AliasChoices("user_id", "created_by"))

    created_at: datetime

    is_active: bool

    engagement_score: float = 0.0