from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_current_user_id
from app.db.models import User as UserModel
from app.db.session import get_db
from app.domains.post.schemas import PostPoolMember
from app.domains.user.profile_schemas import UserProfile
from app.domains.user.schemas import (
    User as UserSchema,
    UserBasic,
    UserCreate,
    UserIdPayload,
)
from app.domains.user.service import UserService
from app.schemas.common import Paginated
from app.schemas.response import ApiResponse, success

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """Your own account and profile."""
    return UserSchema.model_validate(current_user)


@router.get("/my_post_items", response_model=Paginated[PostPoolMember])
async def get_my_post_items(
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Your posts that are visible to everyone.

    Posts still awaiting review, held, or archived are listed separately by
    GET /posts/my_inactive_posts."""
    service = UserService(db)
    pool_members, next_cursor = await service.get_pool_members(
        user_id=current_user_id,
        cursor_key=cursor,
        limit=limit,
    )

    return {
        "items": pool_members,
        "next_cursor": next_cursor,
    }


@router.put("/me/profile", response_model=ApiResponse[UserIdPayload])
async def update_my_profile(
    profile: UserProfile,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Update your profile.

    Only the fields you send are changed; anything you leave out keeps its
    current value. To clear a field, send it explicitly as null."""
    service = UserService(db)
    user_id = await service.update_profile(current_user.id, profile)
    return success("Profile updated", user_id=user_id)


@router.post(
    "/",
    response_model=ApiResponse[UserIdPayload],
    status_code=201,
)
async def add_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Add someone to a college. Staff only.

    An admin can add a user to any college; a moderator or success coach can
    only add one to their own college, and cannot hand out staff roles."""
    service = UserService(db)
    user_id = await service.add_user(current_user, payload)
    return success("User added", user_id=user_id)


@router.get("/{user_id}", response_model=UserBasic)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """A person's public details."""
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )
    return user


@router.get("/{user_id}/profile", response_model=UserSchema)
async def get_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """A person's public profile: their bio, skills, experience and journey."""
    service = UserService(db)
    profile = await service.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "Profile not found"},
        )
    return profile


@router.get("/{user_id}/post_items", response_model=Paginated[PostPoolMember])
async def get_post_items(
    user_id: UUID,
    cursor: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """A person's publicly visible posts, newest first."""
    service = UserService(db)
    pool_members, next_cursor = await service.get_pool_members(
        user_id=user_id,
        cursor_key=cursor,
        limit=limit,
    )

    return {
        "items": pool_members,
        "next_cursor": next_cursor,
    }
