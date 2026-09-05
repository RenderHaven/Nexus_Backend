from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_actor, get_current_user, get_current_user_id
from app.db.models import User as UserModel
from app.db.session import get_db
from app.domains.post.schemas import PostPoolMember
from app.domains.user.profile_schemas import UserProfile
from app.domains.user.admin_service import UserAdminService
from app.domains.user.schemas import (
    BulkUserAction,
    BulkUserResult,
    MyPermissions,
    TempPasswordPayload,
    User as UserSchema,
    UserAdminRow,
    UserBasic,
    UserCreate,
    UserIdPayload,
    UserListFilters,
    UserUpdate,
)
from app.domains.user.service import UserService
from app.rules import Actor, Permission
from app.schemas.common import Page, Paginated
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
    actor: Actor = Depends(get_actor),
):
    """Update your profile.

    Only the fields you send are changed; anything you leave out keeps its
    current value. To clear a field, send it explicitly as null."""
    service = UserService(db)
    user_id = await service.update_profile(actor, profile)
    return success("Profile updated", user_id=user_id)


@router.post(
    "/",
    response_model=ApiResponse[UserIdPayload],
    status_code=201,
)
async def add_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    """Add someone to a college. Staff only.

    An admin can add a user to any college; a moderator or success coach can
    only add one to their own college, and cannot hand out staff roles."""
    service = UserService(db)
    user_id = await service.add_user(actor, payload)
    return success("User added", user_id=user_id)


async def get_staff_actor(actor: Actor = Depends(get_actor)) -> Actor:
    """
    Only admins, moderators and success coaches may manage accounts.

    This is the role gate alone. Which college the caller may act on is
    decided per request from the college of whoever they are acting on.
    """
    actor.require(Permission.MANAGE_USER)
    return actor


@router.get("/me/permissions", response_model=MyPermissions)
async def get_my_permissions(actor: Actor = Depends(get_actor)):
    """What your account is allowed to do, and where.

    Read straight off the permission tables, so the app can hide what you
    cannot use instead of guessing from your role name. college_id is the
    campus you are scoped to; an admin is platform-wide and scoped to none."""
    return UserAdminService.permissions_for(actor)


@router.get("", response_model=Page[UserAdminRow])
async def list_users(
    filters: UserListFilters = Depends(),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """The user table. Staff only.

    Narrow by college, role, alumni status, active state, or free text over
    username and email. A moderator or success coach is scoped to their own
    college: leave college_id out and it is filled in for you, and asking for
    another college is refused. An admin may ask for any, or omit it for all
    of them at once."""
    service = UserAdminService(db)

    items = await service.list_users(
        actor=staff,
        filters=filters,
        limit=limit,
        offset=offset,
    )

    return Page.of(items, limit=limit, offset=offset)


@router.post("/bulk", response_model=BulkUserResult)
async def bulk_user_action(
    payload: BulkUserAction,
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """Apply one action to a selection of accounts. Staff only.

    A refused id does not sink the batch: the response lists what went
    through and what did not, with a reason for each."""
    service = UserAdminService(db)
    return await service.bulk_action(
        actor=staff,
        user_ids=payload.user_ids,
        action=payload.action,
        value=payload.value,
    )


@router.patch("/{user_id}", response_model=ApiResponse[UserIdPayload])
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """Change someone's role, college or alumni status. Staff only.

    A moderator or success coach may only edit members of their own college:
    not another staff account, and not to move someone elsewhere. Only an
    admin can do either."""
    service = UserAdminService(db)
    updated_id = await service.update_user(staff, user_id, payload)
    return success("User updated", user_id=updated_id)


@router.post("/{user_id}/deactivate", response_model=ApiResponse[UserIdPayload])
async def deactivate_user(
    user_id: UUID,
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """Take an account out of service. Staff only.

    The person can no longer sign in, and everything they wrote is hidden
    from the feed and from search. Reversible, and the safe alternative to
    deleting someone. You cannot deactivate your own account."""
    service = UserAdminService(db)
    updated_id = await service.set_active(staff, user_id, is_active=False)
    return success("User deactivated", user_id=updated_id)


@router.post("/{user_id}/activate", response_model=ApiResponse[UserIdPayload])
async def activate_user(
    user_id: UUID,
    staff: Actor = Depends(get_staff_actor),
    db: AsyncSession = Depends(get_db),
):
    """Bring a deactivated account back. Staff only.

    Their posts become visible again exactly as far as they were before:
    anything the author archived, or a moderator held, stays hidden."""
    service = UserAdminService(db)
    updated_id = await service.set_active(staff, user_id, is_active=True)
    return success("User activated", user_id=updated_id)


@router.post(
    "/{user_id}/reset_password",
    response_model=ApiResponse[TempPasswordPayload],
)
async def reset_user_password(
    user_id: UUID,
    actor: Actor = Depends(get_actor),
    db: AsyncSession = Depends(get_db),
):
    """Issue a temporary password. Admins only.

    The password comes back once and is never readable again, so pass it on
    before closing the response. There is no email delivery yet."""
    service = UserAdminService(db)
    temp_password = await service.reset_password(actor, user_id)
    return success(
        "Temporary password issued",
        user_id=user_id,
        temp_password=temp_password,
    )


@router.delete("/{user_id}", response_model=ApiResponse[UserIdPayload])
async def delete_user(
    user_id: UUID,
    actor: Actor = Depends(get_actor),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete an account. Admins only.

    Refused with a conflict as soon as the person has written anything --
    deleting an author would tear holes in other people's threads. Deactivate
    accounts with a history instead. You cannot delete your own account."""
    service = UserAdminService(db)
    deleted_id = await service.delete_user(actor, user_id)
    return success("User deleted", user_id=deleted_id)


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
