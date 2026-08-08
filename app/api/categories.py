from fastapi import APIRouter,Depends
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.category import CategoryService

router = APIRouter()

@router.get("/all")
async def get_all_categories(
    db: AsyncSession = Depends(get_db)
):
    category_svc = CategoryService(db)
    categories = await category_svc.get_all_categories()
    if not categories:
        return {
            "message": "No categories found"
        }

    return categories


