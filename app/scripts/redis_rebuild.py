import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.db.session import engine
from app.domains.reaction.service import ReactionService
from app.domains.feed.service import FeedService


async def rebuild_interactions():
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    async with SessionLocal() as db:
        svc = ReactionService(db)
        await svc.build()

async def rebuild_feed_pools():
    print("Starting Feed Pools Redis build...")
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    async with SessionLocal() as db:
        svc = FeedService(db)
        await svc.build_pools()
    print("Feed Pools Redis build completed.")

async def run_all():
    print("--- Starting full Redis rebuild ---")
    await rebuild_interactions()
    await rebuild_feed_pools()
    print("--- Full Redis rebuild complete ---")

if __name__ == "__main__":
    asyncio.run(run_all())
