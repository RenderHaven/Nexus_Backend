"""Reads and writes for the moderation audit trail."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ModerationAction, ModerationLog


class ModerationLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(
        self,
        post_id: UUID,
        coach_id: UUID,
        action: ModerationAction,
        note: str | None = None,
    ) -> ModerationLog:
        entry = ModerationLog(
            post_id=post_id,
            coach_id=coach_id,
            action=action,
            note=note,
        )
        self.db.add(entry)
        await self.db.commit()
        return entry

    async def list_for_post(
        self,
        post_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModerationLog]:
        """One post's decisions, newest first."""
        result = await self.db.execute(
            select(ModerationLog)
            .options(selectinload(ModerationLog.coach))
            .where(ModerationLog.post_id == post_id)
            .order_by(ModerationLog.created_at.desc(), ModerationLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(
        self,
        college_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModerationLog]:
        """
        The staff activity stream. Scoped by the college of the post that was
        acted on, not the moderator's own -- an admin acting on campus B
        belongs in campus B's feed.
        """
        query = (
            select(ModerationLog)
            .options(selectinload(ModerationLog.coach))
            .order_by(ModerationLog.created_at.desc(), ModerationLog.id.desc())
            .offset(offset)
            .limit(limit)
        )

        if college_id is not None:
            from app.db.models import Post

            query = query.join(Post, Post.id == ModerationLog.post_id).where(
                Post.college_id == college_id
            )

        return list((await self.db.execute(query)).scalars().all())

    async def count_by_moderator(
        self,
        college_id: UUID | None = None,
        since=None,
    ) -> dict[UUID, int]:
        """Decisions per moderator, for the throughput stat."""
        query = select(
            ModerationLog.coach_id,
            func.count(ModerationLog.id),
        ).group_by(ModerationLog.coach_id)

        if since is not None:
            query = query.where(ModerationLog.created_at >= since)

        if college_id is not None:
            from app.db.models import Post

            query = query.join(Post, Post.id == ModerationLog.post_id).where(
                Post.college_id == college_id
            )

        return {row[0]: row[1] for row in (await self.db.execute(query)).all()}
