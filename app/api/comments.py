from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.comments.domain import Comment
from app.auth import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.domains.comments.service import CommentService

router = APIRouter()


class CommentIDsRequest(BaseModel):
    comment_ids: list[UUID]


@router.post("/batch")
async def get_many_comments(
    payload: CommentIDsRequest,
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    return await comment_svc.get_many_comments(payload.comment_ids)


@router.get("/{comment_id}",response_model=Comment)
async def get_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    comment = await comment_svc.get_comment(comment_id)
    if not comment:
        return {"message": "Comment not found"}
    return comment


@router.get("/{comment_id}/reply_ids")
async def get_reply_ids(
    comment_id: UUID,
    cursor: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    reply_ids, next_cursor = await comment_svc.get_reply_ids(comment_id, cursor=cursor, limit=limit)
    return {"reply_ids": reply_ids, "next_cursor": next_cursor}


@router.post("/{comment_id}/reply")
async def comment_reply(
    comment_id: UUID,
    comment: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    post_interaction = await comment_svc.add_comment_reply(
        current_user.id, comment_id, comment
    )
    if not post_interaction:
        return {"message": "Comment reply not added"}
    return {
        "message": "Comment reply added successfully",
        "post_interaction": post_interaction,
    }


@router.post("/{comment_id}/edit")
async def edit_comment(
    comment_id: UUID,
    comment: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    post_interaction = await comment_svc.edit_comment(
        current_user.id, comment_id, comment
    )
    if not post_interaction:
        return {"message": "Comment not edited"}
    return {
        "message": "Comment edited successfully",
        "post_interaction": post_interaction,
    }


@router.post("/{comment_id}/delete")
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    result = await comment_svc.delete(current_user.id, comment_id)
    if not result:
        return {"message": "Comment not deleted"}
    return {
        "message": "Comment deleted successfully",
        "post_interaction": result,
    }
