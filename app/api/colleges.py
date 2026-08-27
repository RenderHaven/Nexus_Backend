from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domains.colleges.service import CollegeService
from app.db.models import User as UserModel
from app.auth.deps import get_current_user

from app.domains.colleges.schemas import CollegeBasic
from app.schemas.common import Paginated
router = APIRouter()

@router.get("/my_college",response_model=CollegeBasic)
async def get_my_college(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CollegeService(db)
    college = await service.get_college(current_user.college_id)
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found",
        )
    return college


@router.get("/{college_id}", response_model=CollegeBasic)
async def get_college(
    college_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CollegeService(db)
    college = await service.get_college(college_id)
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found",
        )
    return college

@router.get("/post_ids", response_model=Paginated[UUID])
async def get_my_college_posts(
    cursor: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    service = CollegeService(db)
    posts, next_cursor = await service.get_post_ids(
        college_id=current_user.college_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": posts,
        "next_cursor": next_cursor,
    }

@router.get("/{college_id}/post_ids", response_model=Paginated[UUID])
async def get_college_posts(
    college_id: UUID,
    cursor: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    service = CollegeService(db)
    posts, next_cursor = await service.get_post_ids(
        college_id=college_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": posts,
        "next_cursor": next_cursor,
    }
