from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Category


class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, category:Category)->Category:
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update(self, category:Category)->Category:
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category:Category)->Category:
        await self.db.delete(category)
        await self.db.commit()
        return category

    async def get_by_id(self, category_id:UUID)->Category:
        category = await self.db.get(Category, category_id)
        return category        
    
    async def get_all(self):
        result = await self.db.execute(
            select(Category)
        )

        return result.scalars().all()
    