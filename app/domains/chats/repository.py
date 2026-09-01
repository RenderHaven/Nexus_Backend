from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatParticipant, ChatRoom, Message


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_room(self, chat_room_id: UUID) -> ChatRoom | None:
        result = await self.db.execute(
            select(ChatRoom).where(ChatRoom.id == chat_room_id)
        )
        return result.scalar_one_or_none()

    async def get_participant(
        self,
        chat_room_id: UUID,
        user_id: UUID,
    ) -> ChatParticipant | None:
        result = await self.db.execute(
            select(ChatParticipant).where(
                ChatParticipant.chat_room_id == chat_room_id,
                ChatParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_my_rooms(self, user_id: UUID) -> list[ChatRoom]:
        result = await self.db.execute(
            select(ChatRoom)
            .join(ChatParticipant, ChatParticipant.chat_room_id == ChatRoom.id)
            .where(ChatParticipant.user_id == user_id)
            .order_by(ChatRoom.created_at.desc(), ChatRoom.id.desc())
        )
        return list(result.scalars().all())

    async def get_message(
        self,
        message_id: UUID,
    ) -> Message | None:
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_messages(
        self,
        chat_room_id: UUID,
        cursor: tuple[UUID, datetime] | None = None,
        limit: int = 20,
    ) -> list[Message]:
        query = (
            select(Message)
            .where(Message.chat_room_id == chat_room_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )

        if cursor is not None:
            message_id, created_at = cursor
            query = query.where(
                or_(
                    Message.created_at < created_at,
                    and_(
                        Message.created_at == created_at,
                        Message.id < message_id,
                    ),
                )
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_message(
        self,
        chat_room_id: UUID,
        sender_id: UUID,
        body: str,
        message_type,
    ) -> Message:
        message = Message(
            id=uuid4(),
            chat_room_id=chat_room_id,
            sender_id=sender_id,
            body=body,
            type=message_type,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_room_by_post(self, post_id: UUID) -> ChatRoom | None:
        result = await self.db.execute(
            select(ChatRoom).where(ChatRoom.post_id == post_id)
        )
        return result.scalars().first()

    async def add_participant(
        self,
        chat_room_id: UUID,
        user_id: UUID,
    ) -> ChatParticipant:
        existing = await self.get_participant(chat_room_id, user_id)

        if existing:
            return existing

        participant = ChatParticipant(
            id=uuid4(),
            chat_room_id=chat_room_id,
            user_id=user_id,
        )
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def remove_participant(
        self,
        chat_room_id: UUID,
        user_id: UUID,
    ) -> bool:
        participant = await self.get_participant(chat_room_id, user_id)

        if not participant:
            return False

        await self.db.delete(participant)
        await self.db.commit()
        return True

    async def create_room(self, post_id: UUID, admin_id: UUID,name:str) -> ChatRoom:
        room_id = uuid4()
        room = ChatRoom(id=room_id, post_id=post_id, admin_id=admin_id,name=name)
        participant = ChatParticipant(id=uuid4(), chat_room_id=room_id, user_id=admin_id)
        self.db.add(room)
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(room)
        return room
