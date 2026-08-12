from app.schemas.schemas import Category
from sqlalchemy import UUID
from app.domains.categories.repository import CategoryRepository
from app.domains.categories.redis import CategoryStore
class CategoryStorage:
    def __init__(self,db):
        self.db=db
        self.category_repo = CategoryRepository(db)
        self.category_store=CategoryStore()
        
    async def get_all_categories(self)->list[Category]:
        try:
            categories = await self.category_store.get_all_categories()
            if not categories:
                categories = await self.category_repo.get_all()
                await self.category_store.set_all_categories(categories)
            return categories
        except Exception as e:
            raise e
    
    async def get_category(self, category_id:UUID)->Category | None:
        try:
            category = await self.category_store.get_category(category_id)
            if not category:
                category = await self.category_repo.get_by_id(category_id)
                await self.category_store.set_category(category_id,category)
            return category
        except Exception as e:
            raise e