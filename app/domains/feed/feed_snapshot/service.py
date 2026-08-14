from uuid import uuid4
from app.domains.feed.feed_snapshot.domain import FeedSnapshot
from app.domains.feed.feed_snapshot.redis import FeedSnapshotStore
from sqlalchemy import UUID
class FeedSnapshotService:
    def __init__(self):
        self.storage:FeedSnapshotStore=FeedSnapshotStore()

    async def get_snapshot(self,feed_id:UUID|None=None)->FeedSnapshot|None:
        if feed_id is None:
            return None
        snapshot = await self.storage.get(str(feed_id))
        if not snapshot:
            return None
        return FeedSnapshot(**snapshot)

    async def update_snapshot(self,user_id:UUID,offsets:dict[str,int],feed_id:UUID|None=None)->UUID|None:
        if offsets:
            feed_id=feed_id if feed_id else uuid4()
            return await self.save_snapshot(feed_id,FeedSnapshot(feed_id=feed_id,user_id=user_id,offsets=offsets))
            
    async def save_snapshot(self,feed_id:UUID|None=None,feed_snapshot:FeedSnapshot|None=None)->UUID|None:
        if feed_id and feed_snapshot:
            await self.storage.add(str(feed_id),feed_snapshot.model_dump(mode="json"))
            return feed_id
    
    async def delete_snapshot(self,feed_id:UUID|None=None)->None:
        if feed_id:
            await self.storage.delete(str(feed_id))