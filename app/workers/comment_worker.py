import asyncio
import json
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.db.session import engine
from app.config import settings

async def run_comment_worker():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_COMMENTS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="comment_group"
    )
    
    await consumer.start()
    print("Comment worker started, consuming from", settings.KAFKA_COMMENTS_TOPIC)

    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        while True:
            batch = await consumer.getmany(timeout_ms=1000, max_records=100)
            if not batch:
                continue

            async with SessionLocal() as db:
                from app.domains.comments.service import CommentService
                svc = CommentService(db)
                count = await svc.process_batch(batch)
                print(f"Processed batch of {count} comment events. DB and Redis updated.")

    except Exception as e:
        print(f"Worker Error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run_comment_worker())
