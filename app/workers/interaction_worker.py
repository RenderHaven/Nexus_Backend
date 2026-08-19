import asyncio
import json
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.db.session import engine
from app.config import settings
from app.domains.interaction.repository import PostInteractionRepository
from uuid import UUID

async def run_interaction_worker():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_INTERACTIONS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="interaction_group"
    )
    
    await consumer.start()
    print("Interaction worker started, consuming from", settings.KAFKA_INTERACTIONS_TOPIC)
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        while True:
            # Poll for a batch of messages (wait up to 1 second, max 100 records)
            batch = await consumer.getmany(timeout_ms=1000, max_records=100)
            if not batch:
                continue

            async with SessionLocal() as db:
                print("commiting")
                repo = PostInteractionRepository(db)
                count = 0
                for tp, messages in batch.items():
                    for msg in messages:
                        data = msg.value
                        action = data.get("action")
                        post_id = UUID(data.get("post_id"))
                        user_id = UUID(data.get("user_id"))

                        if action == "like.created":
                            await repo.update_like(post_id, user_id, True, commit=False)
                        elif action == "like.deleted":
                            await repo.update_like(post_id, user_id, False, commit=False)
                        count += 1
                
                # Commit the entire batch in a single transaction
                await db.commit()
            
            # Here we would send the batch to Preference Engine
            print(f"Processed batch of size {count}. Forwarding to Preference Engine...")

    except Exception as e:
        print(f"Worker Error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run_interaction_worker())
