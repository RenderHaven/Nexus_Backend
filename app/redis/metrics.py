"""
Per-namespace cache hit and miss counters.

Redis reports keyspace_hits and keyspace_misses server-wide, which answers
"is the cache working" but not "which cache is working". A miss on
`post:{id}` costs a Postgres round trip on the feed; a miss on `category:{id}`
costs almost nothing. Those need separate numbers, and only the code doing the
lookup knows which namespace it just asked for -- hence counters written here
rather than derived from INFO.

Two shapes are kept per namespace:

  metrics:cache:{ns}:hits            running total, no expiry
  metrics:cache:{ns}:{YYYYMMDDHH}:hits   one hour, expires after 25h

The hourly buckets are what the screen graphs; the running totals are what
survives a day of no traffic.

Recording is best effort by construction. Every method swallows its own
errors: a monitoring counter must never be the reason a read fails.
"""
from datetime import datetime, timezone

from app.redis.client import get_redis

# 25, not 24, so a full day of buckets is always present while the newest one
# is still filling.
BUCKET_TTL = 25 * 60 * 60
BUCKET_FORMAT = "%Y%m%d%H"


def _bucket(at: datetime | None = None) -> str:
    return (at or datetime.now(timezone.utc)).strftime(BUCKET_FORMAT)


class CacheMetrics:
    def __init__(self):
        self.redis = get_redis()

    def total_key(self, namespace: str, outcome: str) -> str:
        return f"metrics:cache:{namespace}:{outcome}"

    def bucket_key(self, namespace: str, outcome: str, hour: str) -> str:
        return f"metrics:cache:{namespace}:{hour}:{outcome}"

    async def record(self, namespace: str, hits: int = 0, misses: int = 0) -> None:
        """
        Count one batch read of a namespace.

        Takes both numbers at once because that is how a batch read produces
        them -- an MGET of twenty ids is eighteen hits and two misses, one
        call, one pipeline.
        """
        if hits <= 0 and misses <= 0:
            return

        try:
            hour = _bucket()
            pipeline = self.redis.pipeline()

            for outcome, count in (("hits", hits), ("misses", misses)):
                if count <= 0:
                    continue

                pipeline.incrby(self.total_key(namespace, outcome), count)

                bucket = self.bucket_key(namespace, outcome, hour)
                pipeline.incrby(bucket, count)
                pipeline.expire(bucket, BUCKET_TTL)

            await pipeline.execute()
        except Exception:
            # A counter is never worth failing a read over.
            pass


_metrics = CacheMetrics()


async def record(namespace: str, hits: int = 0, misses: int = 0) -> None:
    """Module-level shorthand, so a store records with one line and one import."""
    await _metrics.record(namespace, hits=hits, misses=misses)
