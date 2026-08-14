from app.redis.keys import RedisKeys
from app.redis.client import get_redis
from typing import Iterable
import json

class FeedSnapshotStore:

    def __init__(self):
        self.redis = get_redis()

    async def add(
        self,
        feed_id:str,
        snapshot,
    ) -> None:
        """Add or update a post in the pool."""
        await self.redis.set(RedisKeys.feed_snapshot(feed_id), json.dumps(snapshot))

    async def get(self,feed_id:str):
        snapshot = await self.redis.get(RedisKeys.feed_snapshot(feed_id))
        if snapshot: 
            return json.loads(snapshot)
    
    async def delete(self,feed_id:str):
        await self.redis.delete(RedisKeys.feed_snapshot(feed_id))