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
                db_categories = await self.category_repo.get_all()
                categories=[Category.model_validate(db_cat) for db_cat in db_categories]
                await self.category_store.set_all_categories([cat.model_dump(mode="json") for cat in categories])
            else:
                categories=[Category.model_validate(cat) for cat in categories]
            
            return categories
        except Exception as e:
            raise e
    
    async def get_category(self, category_id:UUID)->Category | None:
        try:
            category = await self.category_store.get_category(category_id)
            if not category:
                db_category = await self.category_repo.get_by_id(category_id)
                if db_category:
                    category=Category.model_validate(db_category)
                    await self.category_store.set_category(category_id,category.model_dump(mode="json"))
                else:
                    category=None
            else:
                category=Category.model_validate(category)
            return category
        except Exception as e:
            raise e