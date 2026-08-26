import asyncio
import json
import subprocess
import os
from aiokafka import AIOKafkaConsumer
from app.config import settings
from app.domains.reaction.redis import ReactionRedis

def parse_interval(interval_str: str) -> int:
    """Parse intervals like '6h', '30m', '10s' into seconds."""
    if not interval_str:
        return 21600 # default 6 hours
    unit = interval_str[-1].lower()
    value = int(interval_str[:-1])
    if unit == 'h': return value * 3600
    if unit == 'm': return value * 60
    if unit == 's': return value
    return value

async def rebuild_scheduler():
    interval = parse_interval(settings.REDIS_REBUILD_INTERVAL)
    print(f"Redis rebuild scheduled every {interval} seconds.")
    while True:
        await asyncio.sleep(interval)
        print("Triggering periodic Redis rebuild...")
        env = os.environ.copy()
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "app.scripts.redis_rebuild",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print("Redis rebuild completed successfully:\n", stdout.decode())
        else:
            print(f"Redis rebuild failed:\n{stderr.decode()}")

async def run_redis_worker():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_INTERACTIONS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="redis_sync_group"
    )
    
    await consumer.start()
    print("Redis worker started, consuming from", settings.KAFKA_INTERACTIONS_TOPIC)
    redis_store = ReactionRedis()

    asyncio.create_task(rebuild_scheduler())

    try:
        while True:
            batch = await consumer.getmany(timeout_ms=1000, max_records=100)
            if not batch:
                continue

            for tp, messages in batch.items():
                for msg in messages:
                    data = msg.value
                    action = data.get("action")
                    post_id = data.get("post_id")
                    user_id = data.get("user_id")

                    if action == "like.created":
                        await redis_store.update(post_id, user_id, like=True)
                    elif action == "like.deleted":
                        await redis_store.update(post_id, user_id, like=False)
                    # comment.created can be added here
                    
            print(f"Redis synced batch of {sum(len(m) for m in batch.values())} events.")

    except Exception as e:
        print(f"Redis Worker Error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run_redis_worker())
