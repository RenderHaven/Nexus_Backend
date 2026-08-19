import asyncio
import json
from aiokafka import AIOKafkaConsumer
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

    try:
        async for msg in consumer:
            data = msg.value
            action = data.get("action")
            user_id = data.get("user_id")
            
            # Here you would invalidate Redis Cache or update Redis keys for the post comments
            if action in ["comment_added", "reply_added", "comment_edited", "comment_deleted"]:
                print(f"Processed {action}. Invalidate Redis comment cache here. Forwarding to Preference Engine...")
                # Note: implement redis cache invalidation logic here

    except Exception as e:
        print(f"Worker Error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run_comment_worker())
