"""
Monitoring for the cache.

Posts, users, comments and the feed pools are all read through Redis, so a
cold or stale cache shows up as wrong-looking content long before it shows up
as an error. This service is what the Cache Engine screen asks: is it up, is
it being hit, what is actually stored under a key, and what expires when.

Three rules run through all of it:

  * Never KEYS. Every sweep is a bounded SCAN with a hard cap, and says so
    when it stops early -- one admin page view must not be able to block the
    server that every read goes through.
  * Never raise because Redis is down. health() reports unreachable; the rest
    return empty. A monitoring screen that 500s alongside the thing it
    monitors is useless exactly when it is needed.
  * Read-only unless the caller asked for a write. invalidate() is the only
    method here that changes anything.
"""
import time
from datetime import datetime, timedelta, timezone

from app.redis.client import get_redis
from app.redis.metrics import BUCKET_FORMAT, CacheMetrics
from app.redis.namespaces import BY_NAME, NAMESPACES, classify
from app.redis.schemas import (
    CacheHealth,
    HitRate,
    HitRateBucket,
    InvalidationResult,
    KeyInspection,
    KeyspaceReport,
    NamespaceHitRate,
    NamespaceSeries,
    NamespaceStat,
    TTLPolicy,
    TTLPolicyRow,
)

# How many keys one request may walk before it gives up and says so. 50k
# SCANs in batches of 500 is a hundred round trips -- fast on a loopback, and
# bounded no matter how big the keyspace gets.
SCAN_CAP = 50_000
SCAN_BATCH = 500

# Per namespace, how many keys get the expensive per-key questions (TTL,
# MEMORY USAGE). Counting is cheap; measuring is not.
SAMPLE_PER_NAMESPACE = 100

# Longest value returned by the key inspector. Enough to see the shape of a
# cached post without shipping a megabyte to a browser.
PREVIEW_LIMIT = 2000

# Collections whose whole contents are never returned; only a head.
PREVIEW_ELEMENTS = 20


def _ratio(hits: int, misses: int) -> float | None:
    total = hits + misses
    if total == 0:
        return None
    return round(hits / total, 4)


class RedisMonitorService:
    def __init__(self):
        self.redis = get_redis()
        self.metrics = CacheMetrics()

    # ------------------------------------------------------------------
    # Connection health
    # ------------------------------------------------------------------

    async def health(self) -> CacheHealth:
        """
        Reachability, memory, evictions and uptime.

        Latency is measured around a real PING rather than the INFO call, so
        it is the round trip an actual read pays and is not inflated by the
        size of the INFO payload.
        """
        started = time.perf_counter()

        try:
            await self.redis.ping()
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            info = await self.redis.info()
            dbsize = await self.redis.dbsize()
        except Exception as exc:
            return CacheHealth(reachable=False, error=f"{type(exc).__name__}: {exc}")

        maxmemory = int(info.get("maxmemory", 0) or 0)
        used = int(info.get("used_memory", 0) or 0)

        return CacheHealth(
            reachable=True,
            latency_ms=latency_ms,
            version=info.get("redis_version"),
            mode=info.get("redis_mode"),
            uptime_seconds=int(info.get("uptime_in_seconds", 0) or 0),
            memory_used_bytes=used,
            memory_used_human=info.get("used_memory_human"),
            memory_peak_bytes=int(info.get("used_memory_peak", 0) or 0),
            maxmemory_bytes=maxmemory,
            maxmemory_policy=info.get("maxmemory_policy"),
            # maxmemory 0 means unbounded, and there is no percentage of that.
            memory_used_percent=(
                round(used / maxmemory * 100, 2) if maxmemory else None
            ),
            evicted_keys=int(info.get("evicted_keys", 0) or 0),
            expired_keys=int(info.get("expired_keys", 0) or 0),
            connected_clients=int(info.get("connected_clients", 0) or 0),
            total_keys=dbsize,
        )

    # ------------------------------------------------------------------
    # Hit rate
    # ------------------------------------------------------------------

    async def hit_rate(self, hours: int = 24) -> HitRate:
        """
        Hits against misses, server-wide and per namespace.

        The server-wide pair comes from INFO and counts every key Redis has
        ever been asked for since it started, including pools and cursors. The
        per-namespace pair comes from our own counters and only covers the
        entity caches that record. They answer different questions and are
        deliberately not reconciled.
        """
        hours = max(1, min(hours, 168))

        try:
            info = await self.redis.info("stats")
        except Exception:
            return HitRate(hours=hours)

        server_hits = int(info.get("keyspace_hits", 0) or 0)
        server_misses = int(info.get("keyspace_misses", 0) or 0)

        recorded = [ns for ns in NAMESPACES if ns.is_entity_cache] + [
            BY_NAME["user_profile"],
            BY_NAME["category_all"],
        ]

        totals = await self._counter_totals([ns.name for ns in recorded])
        series = await self._counter_series([ns.name for ns in recorded], hours)

        return HitRate(
            server_hits=server_hits,
            server_misses=server_misses,
            server_hit_rate=_ratio(server_hits, server_misses),
            hours=hours,
            by_namespace=[
                NamespaceHitRate(
                    namespace=ns.name,
                    label=ns.label,
                    hits=totals[ns.name]["hits"],
                    misses=totals[ns.name]["misses"],
                    hit_rate=_ratio(
                        totals[ns.name]["hits"], totals[ns.name]["misses"]
                    ),
                )
                for ns in recorded
            ],
            series=[
                NamespaceSeries(
                    namespace=ns.name,
                    label=ns.label,
                    buckets=series[ns.name],
                )
                for ns in recorded
            ],
        )

    async def _counter_totals(self, names: list[str]) -> dict[str, dict[str, int]]:
        keys = [
            self.metrics.total_key(name, outcome)
            for name in names
            for outcome in ("hits", "misses")
        ]

        try:
            values = await self.redis.mget(keys)
        except Exception:
            values = [None] * len(keys)

        out: dict[str, dict[str, int]] = {}
        for index, name in enumerate(names):
            out[name] = {
                "hits": int(values[index * 2] or 0),
                "misses": int(values[index * 2 + 1] or 0),
            }
        return out

    async def _counter_series(
        self,
        names: list[str],
        hours: int,
    ) -> dict[str, list[HitRateBucket]]:
        """One MGET for the whole grid of namespaces x hours."""
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        window = [now - timedelta(hours=offset) for offset in range(hours - 1, -1, -1)]
        stamps = [hour.strftime(BUCKET_FORMAT) for hour in window]

        keys = [
            self.metrics.bucket_key(name, outcome, stamp)
            for name in names
            for stamp in stamps
            for outcome in ("hits", "misses")
        ]

        try:
            values = await self.redis.mget(keys) if keys else []
        except Exception:
            values = [None] * len(keys)

        out: dict[str, list[HitRateBucket]] = {}
        cursor = 0
        for name in names:
            buckets = []
            for hour in window:
                buckets.append(
                    HitRateBucket(
                        hour=hour,
                        hits=int(values[cursor] or 0),
                        misses=int(values[cursor + 1] or 0),
                    )
                )
                cursor += 2
            out[name] = buckets
        return out

    # ------------------------------------------------------------------
    # Keyspace
    # ------------------------------------------------------------------

    async def keyspace(self) -> KeyspaceReport:
        """
        How many keys sit in each namespace, and how they are expiring.

        Every key found is counted; only the first SAMPLE_PER_NAMESPACE of
        each namespace is measured for TTL and size, because MEMORY USAGE is
        O(size) per key and a namespace of fifty thousand posts would turn one
        page view into fifty thousand of them.
        """
        try:
            total_keys = await self.redis.dbsize()
        except Exception:
            return KeyspaceReport()

        counts: dict[str, int] = {}
        samples: dict[str, list[str]] = {}
        scanned = 0
        truncated = False

        try:
            async for key in self.redis.scan_iter(count=SCAN_BATCH):
                name = classify(key)
                counts[name] = counts.get(name, 0) + 1

                bucket = samples.setdefault(name, [])
                if len(bucket) < SAMPLE_PER_NAMESPACE:
                    bucket.append(key)

                scanned += 1
                if scanned >= SCAN_CAP:
                    truncated = True
                    break
        except Exception:
            return KeyspaceReport(total_keys=total_keys)

        rows = []
        for namespace in NAMESPACES:
            measured = await self._measure(samples.get(namespace.name, []))
            rows.append(
                NamespaceStat(
                    namespace=namespace.name,
                    label=namespace.label,
                    pattern=namespace.pattern,
                    description=namespace.description,
                    keys=counts.get(namespace.name, 0),
                    declared_ttl_seconds=namespace.ttl_seconds,
                    ttl_note=namespace.ttl_note,
                    **measured,
                )
            )

        if counts.get("other"):
            measured = await self._measure(samples.get("other", []))
            rows.append(
                NamespaceStat(
                    namespace="other",
                    label="Unclassified",
                    pattern="*",
                    description=(
                        "Keys no namespace claims. A row here usually means "
                        "something started writing a key shape that "
                        "app/redis/namespaces.py does not know about yet."
                    ),
                    keys=counts["other"],
                    **measured,
                )
            )

        return KeyspaceReport(
            total_keys=total_keys,
            scanned_keys=scanned,
            truncated=truncated,
            namespaces=rows,
        )

    async def _measure(self, keys: list[str]) -> dict:
        """TTL and size over a sample. One pipeline, not two calls per key."""
        if not keys:
            return {
                "sampled_keys": 0,
                "without_ttl": 0,
                "min_ttl_seconds": None,
                "max_ttl_seconds": None,
                "sampled_bytes": None,
            }

        try:
            pipeline = self.redis.pipeline()
            for key in keys:
                pipeline.ttl(key)
                pipeline.memory_usage(key)
            results = await pipeline.execute()
        except Exception:
            return {
                "sampled_keys": 0,
                "without_ttl": 0,
                "min_ttl_seconds": None,
                "max_ttl_seconds": None,
                "sampled_bytes": None,
            }

        ttls, total_bytes, without_ttl = [], 0, 0

        for index in range(len(keys)):
            ttl = results[index * 2]
            size = results[index * 2 + 1]

            # -1 is "no expiry", -2 is "gone since the scan saw it".
            if ttl is None or ttl < 0:
                if ttl == -1:
                    without_ttl += 1
            else:
                ttls.append(ttl)

            if size:
                total_bytes += int(size)

        return {
            "sampled_keys": len(keys),
            "without_ttl": without_ttl,
            "min_ttl_seconds": min(ttls) if ttls else None,
            "max_ttl_seconds": max(ttls) if ttls else None,
            "sampled_bytes": total_bytes or None,
        }

    # ------------------------------------------------------------------
    # Key inspector
    # ------------------------------------------------------------------

    async def inspect(self, key: str) -> KeyInspection:
        """
        What is actually stored under one key.

        The preview is truncated and, for collections, only a head -- this is
        for eyeballing whether a cached post looks right, not for exporting
        the value.
        """
        try:
            key_type = await self.redis.type(key)
        except Exception as exc:
            return KeyInspection(key=key, exists=False, preview=f"unreadable: {exc}")

        if key_type in (None, "none"):
            return KeyInspection(key=key, exists=False, namespace=classify(key))

        try:
            pipeline = self.redis.pipeline()
            pipeline.ttl(key)
            pipeline.memory_usage(key)
            ttl, size = await pipeline.execute()
        except Exception:
            ttl, size = None, None

        preview, length, truncated = await self._preview(key, key_type)

        return KeyInspection(
            key=key,
            exists=True,
            namespace=classify(key),
            type=key_type,
            ttl_seconds=ttl if (ttl is not None and ttl >= 0) else None,
            has_ttl=bool(ttl is not None and ttl >= 0),
            size_bytes=int(size) if size else None,
            length=length,
            preview=preview,
            truncated_preview=truncated,
        )

    async def _preview(self, key: str, key_type: str):
        """A bounded look at a value, whatever type it is."""
        try:
            if key_type == "string":
                value = await self.redis.get(key)
                value = value or ""
                return value[:PREVIEW_LIMIT], len(value), len(value) > PREVIEW_LIMIT

            if key_type == "hash":
                length = await self.redis.hlen(key)
                sample = await self.redis.hgetall(key)
                items = list(sample.items())[:PREVIEW_ELEMENTS]
                text = "\n".join(f"{k} = {v}" for k, v in items)
                return text[:PREVIEW_LIMIT], length, length > len(items)

            if key_type == "set":
                length = await self.redis.scard(key)
                members = await self.redis.srandmember(key, PREVIEW_ELEMENTS)
                return (
                    "\n".join(members)[:PREVIEW_LIMIT],
                    length,
                    length > len(members),
                )

            if key_type == "zset":
                length = await self.redis.zcard(key)
                members = await self.redis.zrevrange(
                    key, 0, PREVIEW_ELEMENTS - 1, withscores=True
                )
                text = "\n".join(f"{m}  {s}" for m, s in members)
                return text[:PREVIEW_LIMIT], length, length > len(members)

            if key_type == "list":
                length = await self.redis.llen(key)
                items = await self.redis.lrange(key, 0, PREVIEW_ELEMENTS - 1)
                return "\n".join(items)[:PREVIEW_LIMIT], length, length > len(items)
        except Exception as exc:
            return f"unreadable: {exc}", None, False

        return None, None, False

    # ------------------------------------------------------------------
    # Invalidate
    # ------------------------------------------------------------------

    async def invalidate_key(self, key: str) -> InvalidationResult:
        """Drop one key. UNLINK, so a large value is freed off the main thread."""
        try:
            deleted = await self.redis.unlink(key)
        except Exception:
            deleted = await self.redis.delete(key)

        return InvalidationResult(target=key, deleted=int(deleted or 0), scanned=1)

    async def invalidate_namespace(self, namespace: str) -> InvalidationResult:
        """
        Drop a whole namespace, in bounded batches.

        Only namespaces named in app/redis/namespaces.py can be reached, so
        there is no way to pass a pattern that sweeps the whole keyspace. The
        metrics namespace is refused outright -- clearing it would erase the
        history this screen is built to show, which is never what someone
        fixing a stale cache means to do.
        """
        known = BY_NAME.get(namespace)

        if known is None:
            raise ValueError(f"Unknown namespace: {namespace}")

        if namespace == "metrics":
            raise ValueError(
                "The metrics namespace holds this screen's own counters and "
                "is not invalidatable"
            )

        deleted = 0
        scanned = 0
        truncated = False
        batch: list[str] = []

        async for key in self.redis.scan_iter(
            match=known.pattern,
            count=SCAN_BATCH,
        ):
            # SCAN MATCH globs are looser than the ordered table: `user:*`
            # matches profile and liked-post keys too. Re-classify each key so
            # invalidating "users" cannot take its neighbours with it.
            if classify(key) != namespace:
                continue

            batch.append(key)
            scanned += 1

            if len(batch) >= SCAN_BATCH:
                deleted += int(await self.redis.unlink(*batch) or 0)
                batch = []

            if scanned >= SCAN_CAP:
                truncated = True
                break

        if batch:
            deleted += int(await self.redis.unlink(*batch) or 0)

        return InvalidationResult(
            target=namespace,
            deleted=deleted,
            scanned=scanned,
            truncated=truncated,
        )

    # ------------------------------------------------------------------
    # TTL policy
    # ------------------------------------------------------------------

    async def ttl_policy(self) -> TTLPolicy:
        """
        What each namespace is supposed to expire after, next to what its keys
        actually say.

        The point is the disagreement column. A namespace declared with an
        eight-hour TTL whose live keys have none means something is writing
        that key without one -- which is how a cache stops being a cache and
        starts being a leak.
        """
        report = await self.keyspace()

        rows = []
        for stat in report.namespaces:
            namespace = BY_NAME.get(stat.namespace)
            declared = stat.declared_ttl_seconds

            disagrees = False
            disagreement = None

            if stat.sampled_keys:
                if declared is not None and stat.without_ttl:
                    disagrees = True
                    disagreement = (
                        f"{stat.without_ttl} of {stat.sampled_keys} sampled keys "
                        f"have no expiry, but this namespace is written with a "
                        f"{declared}s TTL"
                    )
                elif (
                    declared is not None
                    and stat.max_ttl_seconds is not None
                    and stat.max_ttl_seconds > declared
                ):
                    disagrees = True
                    disagreement = (
                        f"a sampled key expires in {stat.max_ttl_seconds}s, longer "
                        f"than the declared {declared}s"
                    )
                elif (
                    declared is None
                    and not stat.without_ttl
                    and namespace is not None
                    and namespace.ttl_note is None
                ):
                    # Not a fault, but worth showing: the table says nothing
                    # about expiry and every live key has one. Skipped where a
                    # ttl_note already explains why the TTL varies -- pools set
                    # theirs per pool, so "every key expires" is expected there.
                    disagreement = "no declared TTL, but every sampled key expires"

            rows.append(
                TTLPolicyRow(
                    namespace=stat.namespace,
                    label=stat.label,
                    pattern=stat.pattern,
                    declared_ttl_seconds=declared,
                    ttl_note=stat.ttl_note,
                    keys=stat.keys,
                    without_ttl=stat.without_ttl,
                    max_ttl_seconds=stat.max_ttl_seconds,
                    disagrees=disagrees,
                    disagreement=disagreement,
                )
            )

        return TTLPolicy(rows=rows, truncated=report.truncated)
