from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domains.colleges.service import CollegeService
from app.db.models import User as UserModel
from app.auth.deps import get_current_user

from app.domains.colleges.schemas import (
    CollegeBasic,
    CollegeCreate,
    CollegeIdPayload,
    CollegeUpdate,
)
from app.schemas.response import ApiResponse, success
from app.domains.user.schemas import UserPoolMember
from app.schemas.common import Paginated
from app.domains.post.schemas import PostPoolMember
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


@router.get("/post_items", response_model=Paginated[PostPoolMember])
async def get_my_college_post_items(
    cursor: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    service = CollegeService(db)
    
    pool_members, next_cursor = await service.get_post_pool_members(
        college_id=current_user.college_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": pool_members,
        "next_cursor": next_cursor,
    }

    

@router.get("/user_items", response_model=Paginated[UserPoolMember])
async def get_my_college_users(
    cursor: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    service = CollegeService(db)
    pool_members, next_cursor = await service.get_user_pool_members(
        college_id=current_user.college_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": pool_members,
        "next_cursor": next_cursor,
    }

@router.post("/", response_model=ApiResponse[CollegeIdPayload], status_code=201)
async def add_college(
    payload: CollegeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Create a college. Admins only."""
    service = CollegeService(db)
    college_id = await service.add_college(current_user, payload)
    return success("College created", college_id=college_id)


@router.patch("/{college_id}", response_model=ApiResponse[CollegeIdPayload])
async def edit_college(
    college_id: UUID,
    payload: CollegeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Change a college's details. Staff only.

    An admin can edit any college; a moderator or success coach can only edit
    their own. Only the fields you send are changed."""
    service = CollegeService(db)
    updated_id = await service.edit_college(current_user, college_id, payload)
    return success("College updated", college_id=updated_id)


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

@router.get("/{college_id}/post_items", response_model=Paginated[PostPoolMember])
async def get_college_post_items(
    college_id: UUID,
    cursor: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = CollegeService(db)
    pool_members, next_cursor = await service.get_post_pool_members(
        college_id=college_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": pool_members,
        "next_cursor": next_cursor,
    }
