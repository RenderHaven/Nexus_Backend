from pydantic import BaseModel
from uuid import UUID
class FeedSnapshot(BaseModel):
    feed_id: UUID
    user_id: UUID | None
    #offsets are saved as pool_id:category_id ->offset 
    #format is pool_id:category_id
    offsets:dict[str,int] 