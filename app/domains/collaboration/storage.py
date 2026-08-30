from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.collaboration.redis import CollaborationRedis
from app.domains.collaboration.repository import CollaborationRepository

class CollaborationStorage:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_store = CollaborationRedis()
        self.repo = CollaborationRepository(db)

    async def _build_redis_for_user(self, user_id: UUID | str) -> None:
        rows = await self.repo.get_all_collab_responses(user_id)
        if rows:
            mapping = {str(post_id): status for post_id, status in rows}
            key = self.redis_store._key(user_id)
            temp_key = f"{key}:tmp"
            pipe = self.redis_store.redis.pipeline()
            pipe.hset(temp_key, mapping=mapping)
            pipe.rename(temp_key, key)
            await pipe.execute()

    async def get_statuses(self, post_ids: list[UUID | str], user_id: UUID | str) -> dict[str, str]:
        if not post_ids:
            return {}
        
        exists = await self.redis_store.is_exist(user_id)
        if not exists:
            await self._build_redis_for_user(user_id)
            
        return await self.redis_store.get_statuses([str(pid) for pid in post_ids], str(user_id))

    async def set_status(self, user_id: UUID | str, post_id: UUID | str, status: str) -> None:
        await self.redis_store.set_status(user_id, post_id, status)
