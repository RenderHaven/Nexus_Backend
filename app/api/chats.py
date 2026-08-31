from uuid import UUID
import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.auth.jwt import ALGORITHM, SECRET_KEY
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
from app.redis.keys import RedisKeys
from app.redis.client import get_redis


router = APIRouter()


async def get_ws_user_id(token: str) -> UUID:
    if not token:
        raise ValueError("Missing token")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise ValueError("Invalid token")
    return UUID(user_id_str)


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

    msg = await chat_svc.send_message(
        chat_room_id=chat_room_id,
        sender_id=current_user.id,
        body=payload.body,
        message_type=payload.type,
    )
    
    redis = get_redis()
    channel_name = RedisKeys.chat_room(str(chat_room_id))
    # Publish msg to redis for any real-time ws listeners
    # Using default model_dump_json encoding which converts UUIDs to strings
    await redis.publish(channel_name, msg.model_dump_json())
    return msg


@router.websocket("/{chat_room_id}/ws")
async def chat_websocket(
    websocket: WebSocket,
    chat_room_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = await get_ws_user_id(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    chat_svc = ChatService(db)
    try:
        # Check if participant
        await chat_svc._require_participant(chat_room_id, user_id)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    
    redis = get_redis()
    channel_name = RedisKeys.chat_room(str(chat_room_id))
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel_name)
    
    async def listen_redis():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except asyncio.CancelledError:
            pass
            
    listen_task = asyncio.create_task(listen_redis())
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                body = payload.get("body")
                msg_type = payload.get("type", "text")
                if not body:
                    continue
                # Save to db
                msg = await chat_svc.send_message(
                    chat_room_id=chat_room_id,
                    sender_id=user_id,
                    body=body,
                    message_type=msg_type
                )
                
                # Publish to redis
                await redis.publish(channel_name, msg.model_dump_json())
                
            except json.JSONDecodeError:
                pass
            except Exception as e:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        listen_task.cancel()
        await pubsub.unsubscribe(channel_name)