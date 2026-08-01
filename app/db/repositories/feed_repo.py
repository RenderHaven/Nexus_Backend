from app.schemas.schemas import PoolPost
from app.db.model import PostStatus
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.model import Post


class FeedRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_popular_posts(self, limit: int = 100) -> list[Post]:
        result = await self.db.execute(
            select(Post)
            .where(Post.is_active == True)
            .order_by(
                Post.engagement_score.desc(),
                Post.created_at.desc(),
            )
            .limit(limit)
        )

        return result.scalars().all()