from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.db.models import User
from app.db.session import get_db
from app.domains.comments.schemas import Comment, CommentRequest
from app.domains.comments.service import CommentService
from app.schemas.common import Paginated
from app.schemas.response import ApiResponse, success

router = APIRouter()


class CommentIDsRequest(BaseModel):
    comment_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=settings.MAX_BATCH_SIZE,
    )


class CommentIdPayload(BaseModel):
    comment_id: UUID


class CommentDeletedPayload(BaseModel):
    comment_id: UUID
    removed_count: int


@router.post("/batch", response_model=list[Comment])
async def get_many_comments(
    payload: CommentIDsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch several comments at once by id.

    Listings return ids first, then load only the comments they are about to
    show."""
    comment_svc = CommentService(db)
    return await comment_svc.get_many_comments(payload.comment_ids)


@router.get("/{comment_id}", response_model=Comment)
async def get_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """A single comment."""
    comment_svc = CommentService(db)
    comment = await comment_svc.get_comment(comment_id)
    if not comment:
        raise HTTPException(
            status_code=404,
            detail={"code": "comment_not_found", "message": "Comment not found"},
        )
    return comment


@router.get("/{comment_id}/reply_ids", response_model=Paginated[UUID])
async def get_reply_ids(
    comment_id: UUID,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """The ids of a comment's replies, newest first.

    Pass the returned cursor to load the next page."""
    comment_svc = CommentService(db)
    reply_ids, next_cursor = await comment_svc.get_reply_ids(
        comment_id, cursor=cursor, limit=limit
    )
    if not reply_ids:
        return {"items": [], "next_cursor": None}
    return {"items": reply_ids, "next_cursor": next_cursor}


@router.post(
    "/{comment_id}/reply",
    response_model=ApiResponse[CommentIdPayload],
    status_code=201,
)
async def comment_reply(
    comment_id: UUID,
    payload: CommentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reply to a comment."""
    comment_svc = CommentService(db)
    result = await comment_svc.add_comment_reply(
        current_user.id, comment_id, payload.comment
    )
    return success("Reply added", comment_id=result.get("comment_id"))


@router.post("/{comment_id}/edit", response_model=ApiResponse[CommentIdPayload])
async def edit_comment(
    comment_id: UUID,
    payload: CommentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the text of a comment you wrote.

    The previous wording is kept, and the comment is marked as edited."""
    comment_svc = CommentService(db)
    result = await comment_svc.edit_comment(
        current_user.id, comment_id, payload.comment
    )
    return success("Comment edited", comment_id=result.get("comment_id"))


@router.post("/{comment_id}/delete", response_model=ApiResponse[CommentDeletedPayload])
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment you wrote.

    Its replies go with it, so removed_count tells you how many comments
    disappeared in total."""
    comment_svc = CommentService(db)
    result = await comment_svc.delete(current_user.id, comment_id)
    return success(
        "Comment deleted",
        comment_id=comment_id,
        removed_count=result.get("removed_count", 0),
    )
