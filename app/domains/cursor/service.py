from uuid import uuid4
from app.domains.cursor.redis import CursorStore
from typing import Dict, Any

class CursorService:
    def __init__(self):
        self.storage: CursorStore = CursorStore()

    async def get_cursor(self, cursor_key: str | None = None) -> dict[str, Any] | None:
        if not cursor_key:
            return None
        return await self.storage.get_cursor(cursor_key)

    async def save_cursor(self, cursor_key: str, data: dict[str, Any]) -> str:
        await self.storage.add_cursor(cursor_key, data)
        return cursor_key

    async def update_cursor(self, data: dict[str, Any], cursor_key: str | None = None) -> str:
        cursor_key = cursor_key if cursor_key else str(uuid4())
        return await self.save_cursor(cursor_key, data)
            
    async def delete_cursor(self, cursor_key: str | None = None) -> None:
        if cursor_key:
            await self.storage.delete_cursor(cursor_key)