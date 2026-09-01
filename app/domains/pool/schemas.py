from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field ,AliasChoices

    
class PoolMember(BaseModel):
    id: UUID

class ZSetCursor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score:float
    member:str

class PoolObject(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    
