from uuid import UUID
from app.storage.categories import CategoryStorage

class CategoryService:

    def __init__(self,db):
        self.db=db
        self.category_store = CategoryStorage(db)
        
    async def get_category(self, category_id:UUID):
        try:
            category = await self.category_store.get(category_id)
            return category
        except Exception as e:
            raise e
    
    async def get_all_categories(self):
        try:
            categories = await self.category_store.get_all()
            return categories
        except Exception as e:
            raise e

    async def update_category(self, category):
        try:
            updated_category = await self.category_store.update(category)       
            return updated_category
        except Exception as e:
            raise e

    async def delete_category(self, category_id):
        try:
            is_deleted = await self.category_store.delete(category_id)
            return is_deleted
        except Exception as e:
            raise e