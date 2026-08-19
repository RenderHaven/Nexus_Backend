import json
from aiokafka import AIOKafkaProducer
from app.config import settings

class KafkaManager:
    def __init__(self):
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_event(self, topic: str, value: dict):
        if not self.producer:
            raise RuntimeError("Kafka producer is not initialized")
        await self.producer.send_and_wait(topic, value)

kafka_manager = KafkaManager()
