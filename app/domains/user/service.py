from app.domains.categories.repository import CategoryRepository
from uuid import UUID
from app.domains.user.storage import UserStorage

class UserService:

    def __init__(self,db):
        self.db=db
        self.user_store = UserStorage(db)
        
    async def get_user(self, user_id:UUID):
        try:
            user = await self.user_store.get_user(user_id)
            return user
        except Exception as e:
            raise e
    
    async def get_category_preferences(self, user_id:UUID):
        try:
            preferences = await self.user_store.get_category_preferences(user_id)
            return preferences
        except Exception as e:
            raise e