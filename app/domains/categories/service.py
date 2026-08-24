from app.db.models import Category
from uuid import UUID
from app.domains.categories.storage import CategoryStorage

class CategoryService:

    def __init__(self,db):
        self.db=db
        self.category_store=CategoryStorage(db)
        
    async def get_category(self, category_id:UUID)->Category | None:
        try:
            category = await self.category_store.get_category(category_id)
            return category
        except Exception as e:
            raise e
    
    async def get_all_categories(self)->list[Category] | None:
        try:
            categories = await self.category_store.get_all_categories()
            return categories
        except Exception as e:
            raise e