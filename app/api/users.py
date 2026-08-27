from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.user.service import UserService
from app.domains.user.schemas import User as UserSchema
from app.db.models import User as UserModel
from app.auth.deps import get_current_user,get_current_user_id

from app.domains.user.schemas import UserBasic
from app.schemas.common import Paginated

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    return UserSchema.model_validate(current_user)


@router.get("/my_post_ids", response_model=Paginated[UUID])
async def get_my_user_posts(
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = UserService(db)
    print(current_user_id)
    post_ids, next_cursor = await service.get_post_ids(
        user_id=current_user_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": post_ids,
        "next_cursor": next_cursor,
    }


@router.get("/{user_id}", response_model=UserBasic)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("/{user_id}/profile", response_model=UserSchema)
async def get_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    profile = await service.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return profile

@router.get("/{user_id}/post_ids", response_model=Paginated[UUID])
async def get_user_posts(
    user_id: UUID,
    cursor: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    post_ids, next_cursor = await service.get_post_ids(
        user_id=user_id,
        cursor_key=cursor,
        limit=limit,
    )
    
    return {
        "items": post_ids,
        "next_cursor": next_cursor,
    }
