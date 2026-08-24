from app.redis.keys import RedisKeys
from app.redis.client import get_redis
import json

class CursorStore:

    def __init__(self):
        self.redis = get_redis()

    def _key(self, cursor_key: str) -> str:
        # Assuming RedisKeys.pool_cursor or similar is used, we can just use pool_cursor for now or introduce a new key.
        # Wait, I'll use a new key like cursor(cursor_key) if possible, but let's stick to RedisKeys.pool_cursor or a generic RedisKeys.cursor. I should check RedisKeys.
        # I'll just use "cursor:{" + cursor_key + "}" as a generic key pattern
        return f"cursor:{cursor_key}"

    async def add_cursor(self, cursor_key: str, cursor: dict) -> None:
        await self.redis.set(self._key(cursor_key), json.dumps(cursor))

    async def get_cursor(self, cursor_key: str) -> dict | None:
        cursor = await self.redis.get(self._key(cursor_key))
        if cursor: 
            return json.loads(cursor)
        return None
    
    async def delete_cursor(self, cursor_key: str) -> None:
        await self.redis.delete(self._key(cursor_key))