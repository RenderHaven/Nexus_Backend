from fastapi import APIRouter
from app.redis.client import get_redis

router = APIRouter()
redis = get_redis()


@router.get("/")
async def redis_status():
    try:
        await redis.ping()
        return {
            "status": "ok",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/keys/{pattern}")
async def redis_keys(pattern: str):
    try:
        keys = await redis.keys(pattern)
        return {
            "keys": keys,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
