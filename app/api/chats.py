from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.domains.chats.schemas import (
    ChatRoomSummary,
    Message,
    MessagePoolMember,
    SendMessageRequest,
)
from app.domains.chats.service import ChatService
from app.schemas.common import Paginated


router = APIRouter()


@router.get("/my_chat_rooms", response_model=list[ChatRoomSummary])
async def my_chat_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_svc = ChatService(db)
    return await chat_svc.get_my_chat_rooms(current_user.id)


@router.get(
    "/{chat_room_id}/msg_items",
    response_model=Paginated[MessagePoolMember],
)
async def get_chat_message_pool(
    chat_room_id: UUID,
    cursor: str | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_svc = ChatService(db)

    members, next_cursor = await chat_svc.get_message_pool_members(
        chat_room_id=chat_room_id,
        user_id=current_user.id,
        cursor_key=cursor,
        limit=limit,
    )

    return {
        "items": members,
        "next_cursor": next_cursor,
    }


@router.post(
    "/{chat_room_id}/message",
    response_model=Message,
    status_code=201,
)
async def send_message(
    chat_room_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_svc = ChatService(db)

    return await chat_svc.send_message(
        chat_room_id=chat_room_id,
        sender_id=current_user.id,
        body=payload.body,
        message_type=payload.type,
    )