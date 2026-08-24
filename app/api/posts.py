from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.auth.deps import get_current_user_id_optional
from app.db.models import User
from app.db.session import get_db
from app.domains.comments.service import CommentService
from app.domains.interaction.service import PostInteractionsService
from app.domains.post.service import PostService
from app.domains.post_type.enum import PostType
from app.domains.post_type.service import PostTypeService
from app.schemas.schemas import Post

router = APIRouter()


class PostIDsRequest(BaseModel):
    post_ids: list[UUID]


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: UUID,
    user_id: User | None = Depends(get_current_user_id_optional),
    db: AsyncSession = Depends(get_db),
):
    post_svc = PostService(db)
    post = await post_svc.get_post(post_id, user_id)
    if not post:
        return {"message": "No post found"}
    return post


@router.post("/batch", response_model=list[Post])
async def get_posts(
    payload: PostIDsRequest,
    user_id: User | None = Depends(get_current_user_id_optional),
    db: AsyncSession = Depends(get_db),
):
    post_svc = PostService(db)
    return await post_svc.get_posts(
        payload.post_ids,
        user_id,
    )


@router.get("/{post_id}/comment_ids")
async def get_comment_ids(
    post_id: UUID,
    cursor: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    comment_ids, next_cursor = await comment_svc.get_comment_ids(post_id, cursor=cursor, limit=limit)
    if not comment_ids:
        return {"comment_ids": [], "next_cursor": None}
    return {"comment_ids": comment_ids, "next_cursor": next_cursor}


@router.post("/{post_id}/comment")
async def comment_post(
    post_id: UUID,
    comment: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    post_interaction = await comment_svc.comment(post_id, current_user.id, comment)
    if not post_interaction:
        return {"message": "Post not commented"}
    return {
        "message": "Post commented successfully",
        "post_interaction": post_interaction,
    }


@router.post("/{post_id}/like")
async def like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.like(post_id, current_user.id)
    if not post_interaction:
        return {"message": "Post not liked"}
    return {
        "message": "Post liked successfully",
        "post_interaction": post_interaction,
    }


@router.post("/{post_id}/unlike")
async def unlike_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.unlike(post_id, current_user.id)
    if not post_interaction:
        return {"message": "Post not liked"}
    return {
        "message": "Post liked successfully",
        "post_interaction": post_interaction,
    }


@router.get("/type/{post_type}/post_ids")
async def get_type_post_ids(
    post_type: PostType,
    user_id: User | None = Depends(get_current_user_id_optional),
    cursor: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    post_type_svc = PostTypeService(db)
    post_ids, next_cursor = await post_type_svc.get_type_post_ids(
        post_type=post_type,
        user_id=user_id,
        cursor_key=cursor,
        limit=limit,
    )
    if not post_ids:
        return {
            "posts": [],
            "next_cursor": None,
        }
    return {
        "posts": post_ids,
        "next_cursor": next_cursor,
    }
