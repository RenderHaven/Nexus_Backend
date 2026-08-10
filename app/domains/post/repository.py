from app.db.model import PostStatus
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.model import Post


class PostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, post:Post)->Post:
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def update(self, post:Post)->Post:
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def delete(self, post:Post)->Post:
        await self.db.delete(post)
        await self.db.commit()
        return post

    async def get_by_id(self, post_id:UUID)->Post:
        post = await self.db.get(Post, post_id)
        return post        
    
    async def get_one(self) -> Post | None:
        result = await self.db.execute(
            select(Post).options(
                selectinload(Post.media),
            )
            .where(Post.is_active == True)
            .where(Post.status == PostStatus.published)
            .limit(1)
        )

        return result.scalar_one_or_none()
    
    async def list_all_posts(
        self,
        limit: int = 20,
        offset: int = 0,
    ):
        result = await self.db.execute(
            select(Post)
            .options(
                selectinload(Post.media),
            )
            .offset(offset)
            .limit(limit)
        )

        return result.scalars().all()



    async def posts_by_ids(
            self,
            post_ids: list[UUID],
        ):
            result = await self.db.execute(
                select(Post)
                .options(
                    selectinload(Post.media),
                )
                .where(Post.id.in_(post_ids))
            )
    
            return result.scalars().all()
    