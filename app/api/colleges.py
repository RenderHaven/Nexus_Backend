from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domains.colleges.service import CollegeService
from app.db.models import User as UserModel
from app.auth.deps import get_actor, get_current_user

from app.domains.colleges.admin_service import CollegeAdminService
from app.domains.colleges.schemas import (
    CollegeAdminRow,
    CollegeBasic,
    CollegeCreate,
    CollegeIdPayload,
    CollegeListFilters,
    CollegePeopleFilters,
    CollegeStats,
    CollegeUpdate,
)
from app.rules import Actor, Permission
from app.schemas.response import ApiResponse, success
from app.domains.user.schemas import UserBasic, UserPoolMember
from app.schemas.common import Page, Paginated
from app.domains.post.schemas import PostPoolMember
router = APIRouter()

@router.get("", response_model=list[CollegeBasic])
async def get_colleges(
    db: AsyncSession = Depends(get_db),
):
    """Every college on the platform, ordered by name.

    Open to anyone: a signup flow needs it before there is a user to
    authenticate."""
    service = CollegeService(db)
    return await service.get_colleges()


async def get_staff_actor(actor: Actor = Depends(get_actor)) -> Actor:
    """Admins, moderators and success coaches. Which college they may look at
    is decided per request."""
    actor.require(Permission.VIEW_COLLEGE_STATS)
    return actor


@router.get("/admin", response_model=Page[CollegeAdminRow])
async def list_colleges_admin(
    filters: CollegeListFilters = Depends(),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """The Manage-Colleges table. Staff only.

    Each row carries its member, post and pending counts. An admin sees every
    college; a moderator or success coach sees the single row for their own.

    Kept separate from GET /colleges, which stays the plain unpaginated list
    the signup flow reads before anyone is signed in."""
    service = CollegeAdminService(db)

    items = await service.list_colleges(
        actor=staff,
        filters=filters,
        limit=limit,
        offset=offset,
    )

    return Page.of(items, limit=limit, offset=offset)


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

@router.post("", response_model=ApiResponse[CollegeIdPayload], status_code=201)
async def add_college(
    payload: CollegeCreate,
    db: AsyncSession = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    """Create a college. Admins only."""
    service = CollegeService(db)
    college_id = await service.add_college(actor, payload)
    return success("College created", college_id=college_id)


@router.patch("/{college_id}", response_model=ApiResponse[CollegeIdPayload])
async def edit_college(
    college_id: UUID,
    payload: CollegeUpdate,
    db: AsyncSession = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    """Change a college's details. Staff only.

    An admin can edit any college; a moderator or success coach can only edit
    their own. Only the fields you send are changed."""
    service = CollegeService(db)
    updated_id = await service.edit_college(actor, college_id, payload)
    return success("College updated", college_id=updated_id)


@router.get("/{college_id}/stats", response_model=CollegeStats)
async def get_college_stats(
    college_id: UUID,
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """Headline numbers for one campus. Staff only, and own-campus only
    unless you are an admin.

    active_this_week counts people who posted -- there is no last-seen signal
    yet, so it undercounts anyone who only reads."""
    service = CollegeAdminService(db)
    return await service.college_stats(staff, college_id)


@router.get("/{college_id}/staff", response_model=list[UserBasic])
async def get_college_staff(
    college_id: UUID,
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """Who moderates this campus. Staff only."""
    service = CollegeAdminService(db)
    return await service.list_staff(staff, college_id)


@router.get("/{college_id}/users", response_model=list[UserBasic])
async def get_college_people(
    college_id: UUID,
    filters: CollegePeopleFilters = Depends(),
    limit: int = Query(20, ge=1, le=100),
    _actor: Actor = Depends(get_actor),
    db: AsyncSession = Depends(get_db),
):
    """The people on one campus, newest first.

    Backs the campus People tab and the alumni filter. Open to any signed-in
    user for any campus, the same way a public post is readable from
    anywhere. Deactivated accounts are left out."""
    service = CollegeService(db)
    return await service.get_people(college_id, filters=filters, limit=limit)


@router.delete("/{college_id}", response_model=ApiResponse[CollegeIdPayload])
async def delete_college(
    college_id: UUID,
    actor: Actor = Depends(get_actor),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a college. Admins only.

    Refused with a conflict while any member or post still belongs to it; the
    response says how many of each."""
    service = CollegeAdminService(db)
    deleted_id = await service.delete_college(actor, college_id)
    return success("College deleted", college_id=deleted_id)


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
