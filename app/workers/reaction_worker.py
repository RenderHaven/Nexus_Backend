import asyncio
import json
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.db.session import engine
from app.config import settings
from app.domains.reaction.repository import PostInteractionRepository
from uuid import UUID

async def run_reaction_worker():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_INTERACTIONS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="reaction_group"
    )
    
    await consumer.start()
    print("Reaction worker started, consuming from", settings.KAFKA_INTERACTIONS_TOPIC)
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        while True:
            # Poll for a batch of messages (wait up to 1 second, max 100 records)
            batch = await consumer.getmany(timeout_ms=1000, max_records=100)
            if not batch:
                continue

            async with SessionLocal() as db:
                from app.domains.reaction.service import ReactionService
                svc = ReactionService(db)
                
                count = await svc.update_db_batch(batch)
                await svc.update_redis_batch(batch)
            
            # Here we would send the batch to Preference Engine
            print(f"Processed batch of size {count}. Forwarding to Preference Engine...")

    except Exception as e:
        print(f"Worker Error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run_reaction_worker())
