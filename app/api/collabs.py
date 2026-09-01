from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.models import User
from app.db.models.enums import CollaborationRequestStatus
from app.db.session import get_db
from app.domains.collaboration.schemas import (
    CollabRequest,
    CollabRequestCreate,
    CollabRevokeRequest,
    CollabReviewRequest,
    CollabStatusResult,
)
from app.domains.collaboration.service import CollaborationService
from app.schemas.response import ApiResponse, success

router = APIRouter()


# ----------------------------------------------------------------------
# Mine, on both sides
# ----------------------------------------------------------------------

@router.get("/my_sent_requests", response_model=list[CollabRequest])
async def my_sent_requests(
    status: CollaborationRequestStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Collaborations you have asked to join, and where each one stands.

    Filter by status to see only the ones still waiting on the author, or only
    the ones you were accepted into."""
    collab_svc = CollaborationService(db)
    return await collab_svc.list_sent_requests(
        sender_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/my_received_requests", response_model=list[CollabRequest])
async def my_received_requests(
    status: CollaborationRequestStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """People asking to join your collaborations, across all of your posts.

    Filter by requested to work through the ones still waiting on you."""
    collab_svc = CollaborationService(db)
    return await collab_svc.list_received_requests(
        recipient_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset,
    )


# ----------------------------------------------------------------------
# One request
# ----------------------------------------------------------------------

@router.post(
    "/requests/{request_id}/review",
    response_model=ApiResponse[CollabStatusResult],
)
async def review_request(
    request_id: UUID,
    payload: CollabReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject one request to join your collaboration.

    Only the person the request was sent to can decide it. Accepting adds the
    sender to the post's chat room; rejecting is final and cannot be
    reopened."""
    collab_svc = CollaborationService(db)
    result = await collab_svc.review_request(
        request_id=request_id,
        reviewer_id=current_user.id,
        accept=payload.accept,
        note=payload.note,
    )
    return success(
        "Request accepted" if payload.accept else "Request rejected",
        payload=result,
    )


# ----------------------------------------------------------------------
# By post
# ----------------------------------------------------------------------

@router.post(
    "/{post_id}/request",
    response_model=ApiResponse[CollabStatusResult],
    status_code=201,
)
async def send_request(
    post_id: UUID,
    payload: CollabRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ask to join a collaboration post.

    sender_id must be your own user id. The author of the post reviews the
    request and decides. Some collaborations are open only to one college;
    requests from outside it are refused, as are requests on your own post or
    ones you have already sent."""
    collab_svc = CollaborationService(db)
    result = await collab_svc.send_request(
        post_id,
        current_user.id,
        current_user.college_id,
        note=payload.note,
        sender_id=payload.sender_id,
    )
    return success("Request sent to the author", payload=result)


@router.post(
    "/{post_id}/revoke",
    response_model=ApiResponse[CollabStatusResult],
)
async def revoke_request(
    post_id: UUID,
    payload: CollabRevokeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a collaboration request you sent earlier.

    sender_id must be your own user id. Withdrawing after being accepted also
    removes you from the chat room. You may ask to join again later."""
    collab_svc = CollaborationService(db)
    result = await collab_svc.revoke_request(
        post_id,
        current_user.id,
        sender_id=payload.sender_id,
    )
    return success("Request withdrawn", payload=result)


@router.get("/{post_id}/requests", response_model=list[CollabRequest])
async def list_requests(
    post_id: UUID,
    status: CollaborationRequestStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Who has asked to join one of your collaboration posts.

    Only the author of the post can see this. Filter by status to work through
    the ones still waiting on a decision."""
    collab_svc = CollaborationService(db)
    return await collab_svc.list_requests(
        post_id=post_id,
        author_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset,
    )
