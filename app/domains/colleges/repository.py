from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Post, College,User
from .schemas import CollegeBasic

class CollegeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        result = await self.db.execute(select(College).where(College.id == college_id))
        college = result.scalars().first()
        if not college:
            return None
        return CollegeBasic.model_validate(college)

    async def get_posts(self, college_id: UUID, limit: int) -> list[Post]:
        result = await self.db.execute(
            select(Post)
            .where(Post.college_id == college_id)
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_users(self, college_id: UUID, limit: int) -> list[User]:
            result = await self.db.execute(
                select(User)
                .where(User.college_id == college_id)
                .order_by(User.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
