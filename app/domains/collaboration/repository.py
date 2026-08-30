from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CollaborationRequest
from app.db.models.enums import CollaborationRequestStatus

class CollaborationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_collab_responses(self, user_id: UUID | str) -> list[tuple[UUID, str]]:
        result = await self.db.execute(
            select(CollaborationRequest.post_id, CollaborationRequest.status)
            .where(CollaborationRequest.user_id == user_id)
        )
        return [(row[0], row[1].value if hasattr(row[1], 'value') else row[1]) for row in result.fetchall()]

    async def update_status(self, post_id: UUID | str, user_id: UUID | str, status: CollaborationRequestStatus | str, commit: bool = True) -> CollaborationRequest | None:
        db_status = status.value if hasattr(status, 'value') else status
        
        result = await self.db.execute(
            select(CollaborationRequest)
            .where(CollaborationRequest.post_id == post_id, CollaborationRequest.user_id == user_id)
        )
        collab_req = result.scalar_one_or_none()
        
        if collab_req:
            collab_req.status = db_status
        else:
            collab_req = CollaborationRequest(post_id=post_id, user_id=user_id, status=db_status)
            self.db.add(collab_req)
            
        if commit:
            await self.db.commit()
            await self.db.refresh(collab_req)
            
        return collab_req
