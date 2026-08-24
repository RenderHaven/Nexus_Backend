from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Post

class PostTypeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_posts_by_type(
        self,
        post_type: str,
        limit: int = 500,
    ) -> list[Post]:

        stmt = (
            select(Post)
            .where(
                Post.type == post_type,
                Post.is_active.is_(True),
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        posts = result.scalars().all()

        return posts
