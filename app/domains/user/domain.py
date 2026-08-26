from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.db.models import UserRole

class UserBasic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: str | None = None
    college_id: UUID | None = None
    role: UserRole
