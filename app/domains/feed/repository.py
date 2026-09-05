from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Post, PostStatus


class FeedRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_popular_posts(self, limit: int = 100) -> list[Post]:
        result = await self.db.execute(
            select(Post)
            .where(Post.is_active == True)
            .where(Post.status == PostStatus.published)
            .order_by(
                Post.engagement_score.desc(),
                Post.created_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_posts(self, limit: int = 100) -> list[Post]:
            result = await self.db.execute(
                select(Post)
                .where(Post.is_active == True)
                .where(Post.status == PostStatus.published)
                .order_by(
                    Post.created_at.desc(),
                )
                .limit(limit)
            )
            return list(result.scalars().all())


    