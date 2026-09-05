from datetime import datetime
from uuid import UUID

from fastapi import HTTPException

from app.domains.chats.message_pool import ChatMessagePool
from app.domains.chats.repository import ChatRepository
from app.domains.chats.schemas import ChatRoomSummary, Message, MessagePoolMember
from app.domains.cursor.service import CursorService
from app.domains.pool.service import PoolService
from app.domains.user.hydrate import attach_users


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

        if room.admin_id==user_id:
            return room
        
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

        messages = [MessagePoolMember.model_validate(member) for member in members]

        return await self._hydrate_authors(messages), next_cursor

    async def _hydrate_authors(self, messages: list) -> list:
        """Attach each message's sender, resolved in one batch from
        user:{id}. Nothing about a person is stored on the message."""
        return await attach_users(self.db, messages, ("sender_id", "author"))


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

    async def add_participant(self, post_id: UUID, user_id: UUID) -> bool:
        """
        Put a user into the chat room of a collaboration post. Called when
        the post author accepts their request.
        """
        room = await self.repository.get_room_by_post(post_id)

        if not room:
            return False

        await self.repository.add_participant(room.id, user_id)
        return True

    async def remove_participant(self, post_id: UUID, user_id: UUID) -> bool:
        """Take a user out of a collaboration post's chat room."""
        room = await self.repository.get_room_by_post(post_id)

        if not room or room.admin_id == user_id:
            return False

        return await self.repository.remove_participant(room.id, user_id)

    async def create_chat_room(self, post_id: UUID, user_id: UUID,name:str) -> ChatRoomSummary:
        room = await self.repository.create_room(post_id=post_id, admin_id=user_id,name=name)
        return ChatRoomSummary.model_validate(room)
