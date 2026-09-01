import uuid
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.auth.deps import get_current_user_id_optional
from app.db.models import ModerationStatus, PostType, User
from app.db.models import Post as DBPost, PostMedia as DBPostMedia
from app.db.session import get_db
from app.domains.comments.schemas import CommentRequest
from app.domains.comments.service import CommentService
from app.domains.post.admin_service import (
    RESTRICTED_POST_TYPES,
    PostAdminService,
    require_moderator,
)
from app.domains.post.schemas import (
    ModerationUpdate,
    Post,
    PostCreate,
    PostIdPayload,
    PostPoolMember,
)
from app.domains.post.service import PostService
from app.domains.reaction.schemas import ReactionAction, ReactionResult
from app.domains.reaction.service import ReactionService
from app.domains.types.service import PostTypeService
from app.schemas.common import Paginated
from app.schemas.response import ApiResponse, success

router = APIRouter()


class CommentIdPayload(BaseModel):
    comment_id: UUID


class PostIDsRequest(BaseModel):
    post_ids: list[UUID] = Field(..., min_length=1, max_length=settings.MAX_BATCH_SIZE)


async def get_moderator_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Only admins, moderators and success coaches may moderate."""
    return require_moderator(current_user)


def create_db_post_from_schema(payload: PostCreate, current_user: User) -> DBPost:
    db_post = DBPost(
        id=uuid.uuid4(),
        user_id=current_user.id,
        college_id=current_user.college_id,
        category_id=payload.category_id,
        type=payload.type,
        title=payload.title,
        content=payload.content,
        date_at=payload.date_at,
        restricted_to_college_id=payload.restricted_to_college_id,
        resources=[res.model_dump() for res in payload.resources] if payload.resources else None,
        action_status=payload.action_status,
    )
    if payload.media:
        for i, media_item in enumerate(payload.media):
            db_post.media.append(
                DBPostMedia(
                    url=media_item.url,
                    public_id=media_item.public_id,
                    media_type=media_item.type,
                    position=i + 1,
                )
            )
    return db_post


def make_media_permanent_bg(public_ids: list[str]):
    if not public_ids:
        return
    from app.media.service import MediaService
    MediaService().make_permanent(public_ids)


def move_deleted_media_bg(public_ids: list[str]):
    """Take a removed post's media out of the live folder."""
    if not public_ids:
        return
    from app.media.service import MediaService
    MediaService().move_to_deleted(public_ids)


async def _create_post(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User,
    service: PostService | PostAdminService,
) -> dict:
    """
    Shared create path. The post is always stored as pending / not active;
    it only reaches the pools once a moderator approves it.
    """
    db_post = create_db_post_from_schema(payload, current_user)

    created_post_id = await service.add_post(db_post)

    if payload.media:
        bg_tasks.add_task(
            make_media_permanent_bg,
            [media_item.public_id for media_item in payload.media],
        )

    return success("Post submitted for review", post_id=created_post_id)


# ----------------------------------------------------------------------
# Create
# ----------------------------------------------------------------------

@router.post("/", response_model=ApiResponse[PostIdPayload], status_code=201)
async def add_post(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a post.

    New posts are held for review and are not visible to anyone else until a
    moderator approves them; the author can see their own the whole time.
    Event and opportunity posts may only be created by staff."""
    # Events and opportunities are moderator-only, whichever route creates them.
    if payload.type in RESTRICTED_POST_TYPES:
        require_moderator(current_user)
        service: PostService | PostAdminService = PostAdminService(db)
    else:
        service = PostService(db)

    return await _create_post(payload, bg_tasks, current_user, service)


@router.post("/collaborations", response_model=ApiResponse[PostIdPayload], status_code=201)
async def add_collaboration(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a collaboration post and open its chat room.

    Other students can then ask to join, and the author decides who gets in.
    Like any post, it goes live once a moderator approves it."""
    payload.type = PostType.collaboration
    return await _create_post(payload, bg_tasks, current_user, PostService(db))


@router.post("/events", response_model=ApiResponse[PostIdPayload], status_code=201)
async def add_event(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an event post. Staff only.

    Events are announcements for the whole campus, so they are limited to
    admins, moderators and success coaches, and are published under the
    college of the staff member creating them."""
    payload.type = PostType.event
    return await _create_post(payload, bg_tasks, current_user, PostAdminService(db))


@router.post("/opportunities", response_model=ApiResponse[PostIdPayload], status_code=201)
async def add_opportunity(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an opportunity post. Staff only.

    Opportunities carry offers students may act on, so they are limited to
    admins, moderators and success coaches, and are published under the
    college of the staff member creating them."""
    payload.type = PostType.opportunity
    return await _create_post(payload, bg_tasks, current_user, PostAdminService(db))


# ----------------------------------------------------------------------
# Read
# ----------------------------------------------------------------------

@router.post("/batch", response_model=list[Post])
async def get_posts(
    payload: PostIDsRequest,
    user_id: UUID | None = Depends(get_current_user_id_optional),
    db: AsyncSession = Depends(get_db),
):
    """Fetch several posts at once by id.

    Feeds and listings return ids first, then load the posts they need in one
    call. Posts that are not public are skipped unless you are the author."""
    post_svc = PostService(db)
    return await post_svc.get_posts(
        payload.post_ids,
        user_id,
    )


@router.get("/my_inactive_posts", response_model=list[Post])
async def get_my_inactive_posts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List your posts that are not public yet.

    These are the posts waiting on review, held by a moderator, or archived by
    you, so you can track what has not gone live. Your published posts appear
    on your profile instead."""
    post_svc = PostService(db)
    return await post_svc.list_my_inactive_posts(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/type/{post_type}/post_items", response_model=Paginated[PostPoolMember])
async def get_type_post_items(
    post_type: PostType,
    user_id: UUID | None = Depends(get_current_user_id_optional),
    cursor: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List posts of a single type, newest first.

    Backs the dedicated tabs such as events, opportunities and collaborations.
    Pass the returned cursor to load the next page."""
    post_type_svc = PostTypeService(db)
    post_items, next_cursor = await post_type_svc.get_pool_members(
        post_type=post_type,
        user_id=user_id,
        cursor_key=cursor,
        limit=limit,
    )
    if not post_items:
        return {
            "items": [],
            "next_cursor": None,
        }
    return {
        "items": post_items,
        "next_cursor": next_cursor,
    }


# ----------------------------------------------------------------------
# Moderation
# ----------------------------------------------------------------------

@router.get("/moderation/{moderation_status}", response_model=list[Post])
async def list_posts_by_moderation_status(
    moderation_status: ModerationStatus,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    college_id: UUID | None = None,
    _moderator: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """Review queue for one moderation state. Staff only.

    Use it to work through posts awaiting a decision, or to look back at what
    was approved, held or removed. Posts their author has archived or deleted
    are left out, and results can be narrowed to a single college."""
    admin_svc = PostAdminService(db)
    return await admin_svc.list_by_moderation_status(
        moderation_status=moderation_status,
        limit=limit,
        offset=offset,
        college_id=college_id,
    )


@router.patch("/{post_id}/moderation", response_model=ApiResponse[PostIdPayload])
async def update_moderation_status(
    post_id: UUID,
    payload: ModerationUpdate,
    moderator: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve, hold or remove a post. Staff only.

    Approving makes the post public; anything else keeps it hidden. The
    decision is recorded against the moderator who made it."""
    admin_svc = PostAdminService(db)
    updated_id = await admin_svc.update_moderation_status(
        post_id=post_id,
        moderation_status=payload.moderation_status,
        reviewer_id=moderator.id,
    )
    return success(
        f"Post marked {payload.moderation_status.value}",
        post_id=updated_id,
    )


@router.delete("/{post_id}", response_model=ApiResponse[PostIdPayload])
async def delete_post_permanently(
    post_id: UUID,
    bg_tasks: BackgroundTasks,
    _moderator: User = Depends(get_moderator_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a post. Staff only.

    For content that must not remain on the platform at all. Authors removing
    their own posts should use the delete action instead, which is reversible
    on our side."""
    admin_svc = PostAdminService(db)
    public_ids = await admin_svc.delete_post(post_id, moderator_id=_moderator.id)

    # The files leave the live folder but are kept, so a takedown can still be
    # reviewed after the fact.
    bg_tasks.add_task(move_deleted_media_bg, public_ids)
    return success("Post deleted permanently", post_id=post_id)


# ----------------------------------------------------------------------
# Owner actions
# ----------------------------------------------------------------------

@router.post("/{post_id}/archive", response_model=ApiResponse[PostIdPayload])
async def archive_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive your own post.

    Takes the post out of public view without losing it; you can publish it
    again at any time."""
    post_svc = PostService(db)
    updated_id = await post_svc.archive_post(post_id, current_user.id)
    return success("Post archived", post_id=updated_id)


@router.post("/{post_id}/publish", response_model=ApiResponse[PostIdPayload])
async def publish_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish your own post again after archiving it.

    It becomes visible again as soon as it is published, provided a moderator
    has already approved it."""
    post_svc = PostService(db)
    updated_id = await post_svc.publish_post(post_id, current_user.id)
    return success("Post published", post_id=updated_id)


@router.post("/{post_id}/delete", response_model=ApiResponse[PostIdPayload])
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete your own post.

    Removes it from public view and from your listings. Only the author can
    delete their post."""
    post_svc = PostService(db)
    updated_id = await post_svc.delete_post(post_id, current_user.id)
    return success("Post deleted", post_id=updated_id)


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: UUID,
    user_id: UUID | None = Depends(get_current_user_id_optional),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single post with its author, media and your own reaction state.

    Returns not found for posts that are not public, unless you are the
    author."""
    post_svc = PostService(db)
    post = await post_svc.get_post(post_id, user_id)
    if not post:
        raise HTTPException(status_code=404, detail="No post found")
    return post


# ----------------------------------------------------------------------
# Comments
# ----------------------------------------------------------------------

@router.get("/{post_id}/comment_ids", response_model=Paginated[UUID])
async def get_comment_ids(
    post_id: UUID,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List the ids of a post's top-level comments, newest first.

    Ids come back first so the client can load only the comments it is about
    to show. Pass the returned cursor to load the next page."""
    comment_svc = CommentService(db)
    comment_ids, next_cursor = await comment_svc.get_comment_ids(post_id, cursor=cursor, limit=limit)
    if not comment_ids:
        return {"items": [], "next_cursor": None}
    return {"items": comment_ids, "next_cursor": next_cursor}


@router.post(
    "/{post_id}/comment",
    response_model=ApiResponse[CommentIdPayload],
    status_code=201,
)
async def comment_post(
    post_id: UUID,
    payload: CommentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a post."""
    comment_svc = CommentService(db)
    result = await comment_svc.comment(post_id, current_user.id, payload.comment)
    return success("Comment added", comment_id=result.get("comment_id"))


# ----------------------------------------------------------------------
# Reactions
# ----------------------------------------------------------------------

@router.post("/{post_id}/like", response_model=ApiResponse[ReactionResult])
async def like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Like a post.

    Liking a post you already like changes nothing."""
    reaction_svc = ReactionService(db)
    await reaction_svc.like(post_id, current_user.id)
    return success(
        "Post liked",
        payload={
            "status": "success",
            "action": ReactionAction.liked,
            "post_id": post_id,
            "user_id": current_user.id,
        },
    )


@router.post("/{post_id}/unlike", response_model=ApiResponse[ReactionResult])
async def unlike_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove your like from a post."""
    reaction_svc = ReactionService(db)
    await reaction_svc.unlike(post_id, current_user.id)
    return success(
        "Like removed",
        payload={
            "status": "success",
            "action": ReactionAction.unliked,
            "post_id": post_id,
            "user_id": current_user.id,
        },
    )
