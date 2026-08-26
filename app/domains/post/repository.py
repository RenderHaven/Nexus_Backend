from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Post, PostStatus


class PostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _post_options(self):
        return [
            selectinload(Post.media),
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.college),
        ]

    async def create(self, post: Post) -> Post:
        self.db.add(post)
        await self.db.commit()
        return post

    async def update(self, post: Post) -> Post:
        self.db.add(post)
        await self.db.commit()
        return post

    async def delete(self, post: Post) -> Post:
        await self.db.delete(post)
        await self.db.commit()
        return post

    async def get_by_id(self, post_id: UUID) -> Post | None:
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(Post.id == post_id)
        )
        return result.scalar_one_or_none()

    async def get_one(self) -> Post | None:
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(Post.is_active == True)
            .where(Post.status == PostStatus.published)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_all_posts(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def posts_by_ids(
        self,
        post_ids: list[UUID],
    ) -> list[Post]:
        if not post_ids:
            return []
        result = await self.db.execute(
            select(Post)
            .options(*self._post_options())
            .where(Post.id.in_(post_ids))
        )
        return list(result.scalars().all())