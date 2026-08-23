from uuid import uuid4
from app.domains.cursor.domain import PoolCursor, PoolGroupCursor
from app.domains.cursor.redis import CursorStore
from sqlalchemy import UUID

class CursorService:
    def __init__(self):
        self.storage: CursorStore = CursorStore()

    # --- Pool Cursor ---

    async def get_pool_cursor(self, cursor_key: str | None = None) -> PoolCursor | None:
        if cursor_key is None:
            return None
        cursor = await self.storage.get_pool_cursor(cursor_key)
        if not cursor:
            return None
        return PoolCursor(**cursor)

    async def update_pool_cursor(self, user_id: UUID | None, offsets: dict[str, int], cursor_key: str | None = None) -> str | None:
        if offsets is not None:
            cursor_key = cursor_key if cursor_key else str(uuid4())
            return await self.save_pool_cursor(cursor_key, PoolCursor(cursor_key=cursor_key, user_id=user_id, offsets=offsets))
            
    async def save_pool_cursor(self, cursor_key: str | None = None, cursor: PoolCursor | None = None) -> str | None:
        if cursor_key and cursor:
            await self.storage.add_pool_cursor(cursor_key, cursor.model_dump(mode="json"))
            return cursor_key
    
    async def delete_pool_cursor(self, cursor_key: str | None = None) -> None:
        if cursor_key:
            await self.storage.delete_pool_cursor(cursor_key)

    # --- Pool Group Cursor ---

    async def get_pool_group_cursor(self, cursor_key: str | None = None) -> PoolGroupCursor | None:
        if cursor_key is None:
            return None
        cursor = await self.storage.get_pool_group_cursor(cursor_key)
        if not cursor:
            return None
        return PoolGroupCursor(**cursor)

    async def update_pool_group_cursor(self, user_id: UUID | None, offsets: dict[str, int], cursor_key: str | None = None) -> str | None:
        if offsets is not None:
            cursor_key = cursor_key if cursor_key else str(uuid4())
            return await self.save_pool_group_cursor(cursor_key, PoolGroupCursor(cursor_key=cursor_key, user_id=user_id, offsets=offsets))
            
    async def save_pool_group_cursor(self, cursor_key: str | None = None, cursor: PoolGroupCursor | None = None) -> str | None:
        if cursor_key and cursor:
            await self.storage.add_pool_group_cursor(cursor_key, cursor.model_dump(mode="json"))
            return cursor_key
    
    async def delete_pool_group_cursor(self, cursor_key: str | None = None) -> None:
        if cursor_key:
            await self.storage.delete_pool_group_cursor(cursor_key)