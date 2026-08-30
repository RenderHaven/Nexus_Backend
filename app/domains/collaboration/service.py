from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.collaboration.repository import CollaborationRepository
from app.domains.collaboration.redis import CollaborationRedis
from app.domains.collaboration.storage import CollaborationStorage
from app.db.models.enums import CollaborationRequestStatus

class CollabStatusService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = CollaborationStorage(db)

    async def get_statuses(self, post_ids: list[UUID | str], user_id: UUID | str):
        return await self.storage.get_statuses(post_ids, user_id)


class CollaborationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CollaborationRepository(db)
        self.redis_store = CollaborationRedis()
        self.storage = CollaborationStorage(db)

    
    async def send_request(self, post_id: UUID | str, user_id: UUID | str):
        status = CollaborationRequestStatus.requested
        status_val = status.value if hasattr(status, 'value') else status
        # Update DB
        await self.repo.update_status(post_id, user_id, status_val, commit=True)
        # Update Redis
        await self.storage.set_status(user_id, post_id, status_val)
        return {"status": "success", "post_id": post_id, "user_id": user_id, "collab_status": status}

    async def revoke_request(self, post_id: UUID | str, user_id: UUID | str):
        status = CollaborationRequestStatus.revoked
        status_val = status.value if hasattr(status, 'value') else status
        # Update DB
        await self.repo.update_status(post_id, user_id, status_val, commit=True)
        # Update Redis
        await self.storage.set_status(user_id, post_id, status_val)
        return {"status": "success", "post_id": post_id, "user_id": user_id, "collab_status": status}
    
    async def update_status(self, post_id: UUID | str, user_id: UUID | str, status: CollaborationRequestStatus):
        status_val = status.value if hasattr(status, 'value') else status
        # Update DB
        await self.repo.update_status(post_id, user_id, status_val, commit=True)
        # Update Redis
        await self.storage.set_status(user_id, post_id, status_val)
        return {"status": "success", "post_id": post_id, "user_id": user_id, "collab_status": status}

    async def build(self):
        from sqlalchemy import select
        from app.db.models import CollaborationRequest

        print("Starting Collaboration Redis build...")
        result = await self.db.execute(
            select(CollaborationRequest.post_id, CollaborationRequest.user_id, CollaborationRequest.status)
        )
        all_requests = result.fetchall()

        collabs_by_user = {}
        for post_id, user_id, status in all_requests:
            val = status.value if hasattr(status, 'value') else status
            collabs_by_user.setdefault(str(user_id), {})[str(post_id)] = val

        pipeline = self.redis_store.redis.pipeline()
        for user_id, mapping in collabs_by_user.items():
            key = self.redis_store._key(user_id)
            temp_key = f"{key}:tmp"
            if mapping:
                pipeline.hset(temp_key, mapping=mapping)
            pipeline.rename(temp_key, key)
        
        await pipeline.execute()
        print(f"Collaboration Redis build completed. Restored {len(all_requests)} collab statuses across {len(collabs_by_user)} users.")
