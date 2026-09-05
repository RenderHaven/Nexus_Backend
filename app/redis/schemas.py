"""Response shapes for the Cache Engine screen."""
from datetime import datetime

from pydantic import BaseModel, Field


class CacheHealth(BaseModel):
    """
    Is Redis reachable, and is it under pressure.

    reachable is the only field guaranteed to be meaningful: when it is false
    everything else is left at its default and `error` says why, because a
    monitoring screen that 500s when the thing it monitors is down is useless
    at exactly the moment it is needed.
    """

    reachable: bool = False
    error: str | None = None

    latency_ms: float | None = None
    version: str | None = None
    mode: str | None = None
    uptime_seconds: int | None = None

    memory_used_bytes: int | None = None
    memory_used_human: str | None = None
    memory_peak_bytes: int | None = None
    maxmemory_bytes: int | None = None
    maxmemory_policy: str | None = None
    # None when maxmemory is 0, i.e. unbounded -- there is no percentage of
    # "no limit".
    memory_used_percent: float | None = None

    evicted_keys: int | None = None
    expired_keys: int | None = None
    connected_clients: int | None = None
    total_keys: int | None = None


class NamespaceHitRate(BaseModel):
    namespace: str
    label: str
    hits: int = 0
    misses: int = 0
    hit_rate: float | None = None
    instrumented: bool = True


class HitRateBucket(BaseModel):
    """One hour of one namespace."""

    hour: datetime
    hits: int = 0
    misses: int = 0


class NamespaceSeries(BaseModel):
    namespace: str
    label: str
    buckets: list[HitRateBucket] = Field(default_factory=list)


class HitRate(BaseModel):
    """
    Server-wide numbers come from INFO and are cumulative since Redis last
    started. The per-namespace ones are our own counters, so they answer a
    different question -- which cache is missing -- and the two will not add
    up to each other.
    """

    server_hits: int = 0
    server_misses: int = 0
    server_hit_rate: float | None = None

    by_namespace: list[NamespaceHitRate] = Field(default_factory=list)
    series: list[NamespaceSeries] = Field(default_factory=list)
    hours: int = 24


class NamespaceStat(BaseModel):
    """One row of the namespace table: how much is in it and how it expires."""

    namespace: str
    label: str
    pattern: str
    description: str
    keys: int = 0

    declared_ttl_seconds: int | None = None
    ttl_note: str | None = None

    # Observed on a sample of live keys, so a namespace that is supposed to
    # expire but does not shows the disagreement rather than hiding it.
    sampled_keys: int = 0
    without_ttl: int = 0
    min_ttl_seconds: int | None = None
    max_ttl_seconds: int | None = None
    sampled_bytes: int | None = None


class KeyspaceReport(BaseModel):
    total_keys: int = 0
    scanned_keys: int = 0
    # True when the scan hit its cap: the numbers below are a floor, not a
    # count. Better a bounded answer than a request that walks a million keys.
    truncated: bool = False
    namespaces: list[NamespaceStat] = Field(default_factory=list)


class KeyInspection(BaseModel):
    key: str
    exists: bool = False
    namespace: str | None = None
    type: str | None = None
    ttl_seconds: int | None = None
    # -1 in Redis means "no expiry"; surfaced as an explicit flag so a client
    # never has to know that.
    has_ttl: bool = False
    size_bytes: int | None = None
    length: int | None = None
    preview: str | None = None
    truncated_preview: bool = False


class InvalidationResult(BaseModel):
    """What a delete actually dropped."""

    target: str
    deleted: int = 0
    scanned: int = 0
    truncated: bool = False


class TTLPolicyRow(BaseModel):
    namespace: str
    label: str
    pattern: str
    declared_ttl_seconds: int | None = None
    ttl_note: str | None = None
    keys: int = 0
    without_ttl: int = 0
    max_ttl_seconds: int | None = None
    # Set when what is on the keys contradicts what the code says it writes.
    disagrees: bool = False
    disagreement: str | None = None


class TTLPolicy(BaseModel):
    rows: list[TTLPolicyRow] = Field(default_factory=list)
    truncated: bool = False
