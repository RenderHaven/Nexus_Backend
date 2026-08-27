from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domains.categories.service import CategoryService
from app.domains.categories.schemas import CategoryBasic

router = APIRouter()

@router.get("", response_model=list[CategoryBasic])
async def get_all_categories(
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    return await service.get_all_categories()

@router.get("/{category_id}", response_model=CategoryBasic)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    category = await service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
