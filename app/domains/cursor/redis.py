from app.redis.keys import RedisKeys
from app.redis.client import get_redis
from typing import Iterable
import json

class CursorStore:

    def __init__(self):
        self.redis = get_redis()

    def _pool_key(self, cursor_key: str) -> str:
        return RedisKeys.pool_cursor(cursor_key)

    def _pool_group_key(self, cursor_key: str) -> str:
        return RedisKeys.pool_group_cursor(cursor_key)

    async def add_pool_cursor(self, cursor_key: str, cursor: dict) -> None:
        await self.redis.set(self._pool_key(cursor_key), json.dumps(cursor))

    async def get_pool_cursor(self, cursor_key: str) -> dict | None:
        cursor = await self.redis.get(self._pool_key(cursor_key))
        if cursor: 
            return json.loads(cursor)
        return None
    
    async def delete_pool_cursor(self, cursor_key: str) -> None:
        await self.redis.delete(self._pool_key(cursor_key))

    async def add_pool_group_cursor(self, cursor_key: str, cursor: dict) -> None:
        await self.redis.set(self._pool_group_key(cursor_key), json.dumps(cursor))

    async def get_pool_group_cursor(self, cursor_key: str) -> dict | None:
        cursor = await self.redis.get(self._pool_group_key(cursor_key))
        if cursor: 
            return json.loads(cursor)
        return None
    
    async def delete_pool_group_cursor(self, cursor_key: str) -> None:
        await self.redis.delete(self._pool_group_key(cursor_key))