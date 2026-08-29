from app.domains.chats.pool import BaseMessagePool
from app.domains.chats.schemas import MessagePoolObject


class ChatMessagePool(BaseMessagePool):
    def __init__(self, chat_room_id, repository, pool_size: int = 100):
        self.chat_room_id = chat_room_id
        self.repository = repository
        self.pool_name = f"chat:{chat_room_id}:messages"
        self.pool_size = pool_size

    async def get_messages(self) -> list[MessagePoolObject]:
        messages = await self.repository.get_messages(
            chat_room_id=self.chat_room_id,
            limit=self.pool_size,
        )
        return [MessagePoolObject.model_validate(message) for message in messages]

    def filter(self, message: MessagePoolObject) -> bool:
        return message.chat_room_id == self.chat_room_id

    def score(self, message: MessagePoolObject) -> float:
        return message.created_at.timestamp()
