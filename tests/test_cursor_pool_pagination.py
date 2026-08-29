import unittest
import asyncio

from app.domains.pool.schemas import ZSetCursor
from app.domains.pool.core.base_pool import BasePool
from app.domains.pool.core.schemas import PoolGroup
from app.domains.pool.core.pool_config import PoolConfig
from app.domains.post.schemas import PostPoolObject
from app.domains.pool.redis import PoolStore
from app.domains.pool.service import PoolService


class DummyPool(BasePool):
    def __init__(self, name="test_pool"):
        self.pool_name = name

    def filter(self, post: PostPoolObject) -> bool:
        return True

    def score(self, post: PostPoolObject) -> float:
        return post.engagement_score

    async def get_posts(self) -> list[PostPoolObject]:
        return []


class InMemoryRedisZSet:
    """In-memory Redis ZSET simulator for testing score + member sorting & pagination."""

    def __init__(self):
        self.zset: dict[str, dict[str, float]] = {}

    def _get_key_zset(self, key: str) -> dict[str, float]:
        if key not in self.zset:
            self.zset[key] = {}
        return self.zset[key]

    async def zadd(self, key: str, mapping: dict[str, float]):
        z = self._get_key_zset(key)
        for member, score in mapping.items():
            z[member] = float(score)

    async def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False):
        z = self._get_key_zset(key)
        sorted_items = sorted(
            z.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True,
        )
        sliced = sorted_items[start : stop + 1 if stop != -1 else None]
        if withscores:
            return [(m, s) for m, s in sliced]
        return [m for m, s in sliced]

    async def zrevrank(self, key: str, member: str):
        z = self._get_key_zset(key)
        sorted_items = sorted(
            z.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True,
        )
        for rank, (m, _) in enumerate(sorted_items):
            if m == member:
                return rank
        return None

    async def zrevrangebyscore(self, key: str, max: float, min: str, withscores: bool = False):
        z = self._get_key_zset(key)
        sorted_items = sorted(
            z.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True,
        )
        filtered = [item for item in sorted_items if item[1] <= float(max)]
        if withscores:
            return [(m, s) for m, s in filtered]
        return [m for m, s in filtered]

    async def exists(self, key: str):
        z = self._get_key_zset(key)
        return 1 if z else 0

    async def delete(self, key: str):
        if key in self.zset:
            del self.zset[key]

    async def expire(self, key: str, ttl: int):
        pass


class TestCursorPoolPagination(unittest.IsolatedAsyncioTestCase):

    async def test_pool_store_cursor_pagination_basic(self):
        store = PoolStore()
        fake_redis = InMemoryRedisZSet()
        store.redis = fake_redis
        pool = DummyPool("pool1")

        posts = [
            ("post_1", 100.0),
            ("post_2", 90.0),
            ("post_3", 80.0),
            ("post_4", 70.0),
            ("post_5", 60.0),
        ]
        await store.create(pool, posts)

        # Page 1 (limit = 2)
        page1 = await store.get_many_with_cursor(pool, cursor=None, limit=2)
        self.assertEqual(page1, [("post_1", 100.0), ("post_2", 90.0)])

        # Page 2 (cursor = last item of page 1)
        cursor = ZSetCursor(score=page1[-1][1], member=page1[-1][0])
        page2 = await store.get_many_with_cursor(pool, cursor=cursor, limit=2)
        self.assertEqual(page2, [("post_3", 80.0), ("post_4", 70.0)])

        # Page 3
        cursor2 = ZSetCursor(score=page2[-1][1], member=page2[-1][0])
        page3 = await store.get_many_with_cursor(pool, cursor=cursor2, limit=2)
        self.assertEqual(page3, [("post_5", 60.0)])

    async def test_pool_store_identical_scores_tiebreaker(self):
        store = PoolStore()
        fake_redis = InMemoryRedisZSet()
        store.redis = fake_redis
        pool = DummyPool("pool1")

        posts = [
            ("post_a", 100.0),
            ("post_b", 100.0),
            ("post_c", 100.0),
            ("post_d", 50.0),
        ]
        await store.create(pool, posts)

        page1 = await store.get_many_with_cursor(pool, cursor=None, limit=2)
        self.assertEqual(page1, [("post_c", 100.0), ("post_b", 100.0)])

        cursor = ZSetCursor(score=page1[-1][1], member=page1[-1][0])
        page2 = await store.get_many_with_cursor(pool, cursor=cursor, limit=2)
        self.assertEqual(page2, [("post_a", 100.0), ("post_d", 50.0)])

    async def test_pool_store_insertion_between_requests(self):
        store = PoolStore()
        fake_redis = InMemoryRedisZSet()
        store.redis = fake_redis
        pool = DummyPool("pool1")

        posts = [
            ("post_1", 100.0),
            ("post_2", 90.0),
            ("post_4", 70.0),
        ]
        await store.create(pool, posts)

        page1 = await store.get_many_with_cursor(pool, cursor=None, limit=2)
        self.assertEqual(page1, [("post_1", 100.0), ("post_2", 90.0)])

        # New post inserted with higher score (post_new, 150.0) before page 2 request
        await store.add(pool, "post_new", 150.0)

        cursor = ZSetCursor(score=page1[-1][1], member=page1[-1][0])
        page2 = await store.get_many_with_cursor(pool, cursor=cursor, limit=2)

        # Should continue cleanly after post_2 without skipping or duplicating
        self.assertEqual(page2, [("post_4", 70.0)])

    async def test_pool_store_fallback_when_cursor_member_deleted(self):
        store = PoolStore()
        fake_redis = InMemoryRedisZSet()
        store.redis = fake_redis
        pool = DummyPool("pool1")

        posts = [
            ("post_1", 100.0),
            ("post_2", 90.0),
            ("post_3", 80.0),
        ]
        await store.create(pool, posts)

        page1 = await store.get_many_with_cursor(pool, cursor=None, limit=2)
        self.assertEqual(page1, [("post_1", 100.0), ("post_2", 90.0)])

        # Remove post_2 from Redis
        del fake_redis._get_key_zset(store._key(pool.pool_name))["post_2"]

        cursor = ZSetCursor(score=90.0, member="post_2")
        page2 = await store.get_many_with_cursor(pool, cursor=cursor, limit=2)

        # Fallback score-based check should return post_3
        self.assertEqual(page2, [("post_3", 80.0)])

    async def test_pool_service_end_to_end_single_pool(self):
        pool_svc = PoolService()
        fake_redis = InMemoryRedisZSet()
        pool_svc.pool_store.redis = fake_redis
        pool = DummyPool("user_pool")

        posts = [
            ("post_10", 100.0),
            ("post_20", 90.0),
            ("post_30", 80.0),
            ("post_40", 70.0),
        ]
        await pool_svc.pool_store.create(pool, posts)

        # Request 1: First page
        ids1, cursor_key1 = await pool_svc.get_post_ids(pool, cursor_key=None, limit=2)
        self.assertEqual(ids1, ["post_10", "post_20"])
        self.assertIsNotNone(cursor_key1)

        # Request 2: Next page using returned cursor_key
        ids2, cursor_key2 = await pool_svc.get_post_ids(pool, cursor_key=cursor_key1, limit=2)
        self.assertEqual(ids2, ["post_30", "post_40"])
        self.assertIsNotNone(cursor_key2)


if __name__ == "__main__":
    unittest.main()
