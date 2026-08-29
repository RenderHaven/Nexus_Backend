from datetime import datetime
from uuid import UUID

from fastapi import HTTPException

from app.domains.chats.message_pool import ChatMessagePool
from app.domains.chats.repository import ChatRepository
from app.domains.chats.schemas import ChatRoomSummary, Message, MessagePoolMember
from app.domains.cursor.service import CursorService
from app.domains.pool.service import PoolService


class ChatService:
    def __init__(self, db):
        self.db = db
        self.repository = ChatRepository(db)
        self.cursor_service = CursorService()
        self.pool_service = PoolService()

    async def get_my_chat_rooms(self, user_id: UUID) -> list[ChatRoomSummary]:
        rooms = await self.repository.get_my_rooms(user_id)
        return [ChatRoomSummary.model_validate(room) for room in rooms]

    async def _require_participant(
        self,
        chat_room_id: UUID,
        user_id: UUID,
    ):
        room = await self.repository.get_room(chat_room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Chat room not found")

        participant = await self.repository.get_participant(
            chat_room_id=chat_room_id,
            user_id=user_id,
        )
        if not participant:
            raise HTTPException(
                status_code=403,
                detail="User is not a participant in this chat room",
            )

        return room

    async def get_message_pool_members(
        self,
        chat_room_id: UUID,
        user_id: UUID,
        cursor_key: str | None = None,
        limit: int = 20,
    ):
        await self._require_participant(chat_room_id, user_id)

        pool = ChatMessagePool(
            chat_room_id=chat_room_id,
            repository=self.repository,
        )

        members, next_cursor = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
        )

        return [MessagePoolMember.model_validate(member) for member in members], next_cursor


    async def send_message(
        self,
        chat_room_id: UUID,
        sender_id: UUID,
        body: str,
        message_type,
    ) -> Message:
        await self._require_participant(chat_room_id, sender_id)

        message = await self.repository.create_message(
            chat_room_id=chat_room_id,
            sender_id=sender_id,
            body=body,
            message_type=message_type,
        )

        return Message.model_validate(message)
