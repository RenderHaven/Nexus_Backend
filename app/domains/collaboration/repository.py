from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import CollaborationRequest, User
from app.db.models.enums import CollaborationRequestStatus


class CollaborationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _options(self):
        return [
            selectinload(CollaborationRequest.sender).selectinload(User.college),
            selectinload(CollaborationRequest.recipient).selectinload(User.college),
        ]

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_request(
        self,
        post_id: UUID | str,
        sender_id: UUID | str,
    ) -> CollaborationRequest | None:
        result = await self.db.execute(
            select(CollaborationRequest).where(
                CollaborationRequest.post_id == post_id,
                CollaborationRequest.sender_id == sender_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, request_id: UUID) -> CollaborationRequest | None:
        result = await self.db.execute(
            select(CollaborationRequest)
            .options(*self._options())
            .where(CollaborationRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def _list(
        self,
        conditions: list,
        limit: int,
        offset: int,
    ) -> list[CollaborationRequest]:
        result = await self.db.execute(
            select(CollaborationRequest)
            .options(*self._options())
            .where(*conditions)
            .order_by(
                CollaborationRequest.created_at.desc(),
                CollaborationRequest.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_post(
        self,
        post_id: UUID,
        status: CollaborationRequestStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollaborationRequest]:
        conditions = [CollaborationRequest.post_id == post_id]
        if status is not None:
            conditions.append(CollaborationRequest.status == status)
        return await self._list(conditions, limit, offset)

    async def list_sent(
        self,
        sender_id: UUID,
        status: CollaborationRequestStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollaborationRequest]:
        """Requests this user sent to other people's posts."""
        conditions = [CollaborationRequest.sender_id == sender_id]
        if status is not None:
            conditions.append(CollaborationRequest.status == status)
        return await self._list(conditions, limit, offset)

    async def list_received(
        self,
        recipient_id: UUID,
        status: CollaborationRequestStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollaborationRequest]:
        """Requests other people sent to this user's posts."""
        conditions = [CollaborationRequest.recipient_id == recipient_id]
        if status is not None:
            conditions.append(CollaborationRequest.status == status)
        return await self._list(conditions, limit, offset)

    async def get_all_collab_responses(
        self,
        sender_id: UUID | str,
    ) -> list[tuple[UUID, str]]:
        result = await self.db.execute(
            select(CollaborationRequest.post_id, CollaborationRequest.status)
            .where(CollaborationRequest.sender_id == sender_id)
        )
        return [
            (row[0], row[1].value if hasattr(row[1], "value") else row[1])
            for row in result.fetchall()
        ]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def upsert_status(
        self,
        post_id: UUID | str,
        sender_id: UUID | str,
        recipient_id: UUID | str,
        status: CollaborationRequestStatus | str,
        note: str | None = None,
        admin_note: str | None = None,
        reviewed_at=None,
        commit: bool = True,
    ) -> CollaborationRequest:
        db_status = status.value if hasattr(status, "value") else status

        collab_req = await self.get_request(post_id, sender_id)

        if collab_req:
            collab_req.status = db_status
        else:
            collab_req = CollaborationRequest(
                post_id=post_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                status=db_status,
            )
            self.db.add(collab_req)

        if note is not None:
            collab_req.user_note = note

        if admin_note is not None:
            collab_req.admin_note = admin_note

        if reviewed_at is not None:
            collab_req.reviewed_at = reviewed_at

        if commit:
            await self.db.commit()
            await self.db.refresh(collab_req)

        return collab_req
