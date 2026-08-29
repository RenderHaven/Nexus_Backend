from abc import abstractmethod

from app.domains.chats.schemas import MessagePoolMember, MessagePoolObject
from app.domains.pool.core.base_pool import BasePool


class BaseMessagePool(BasePool):
    """
    Base pool for messages belonging to a chat room.

    Redis stores MessagePoolMember JSON values in a ZSET. The score is
    the message creation timestamp, giving us stable score/member
    pagination instead of offset pagination.
    """

    async def get_objects(self) -> list[MessagePoolObject]:
        return await self.get_messages()

    def to_member(self, message: MessagePoolObject) -> MessagePoolMember:
        return MessagePoolMember(
            id=message.id,
            chat_room_id=message.chat_room_id,
            sender_id=message.sender_id,
            body=message.body,
            type=message.type,
            created_at=message.created_at,
        )

    @classmethod
    def member_type(cls) -> type[MessagePoolMember]:
        return MessagePoolMember

    @abstractmethod
    async def get_messages(self) -> list[MessagePoolObject]:
        ...
