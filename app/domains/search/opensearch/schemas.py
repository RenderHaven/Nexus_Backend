"""Response shapes for the Search Engine screen."""
from datetime import datetime

from pydantic import BaseModel, Field


class IndexHealth(BaseModel):
    name: str
    alias: str
    physical: str | None = None
    version: int | None = None
    exists: bool = False
    status: str | None = None
    documents: int = 0
    deleted_documents: int = 0
    size_bytes: int | None = None
    shards: int | None = None
    replicas: int | None = None
    unassigned_shards: int | None = None


class SearchHealth(BaseModel):
    """
    Cluster status and per-index state.

    configured is false when OPENSEARCH_URL is unset, which is a supported way
    to run this app -- search degrades and every other route works -- so it is
    reported as a state rather than an error.
    """

    configured: bool = False
    reachable: bool = False
    error: str | None = None

    cluster_name: str | None = None
    version: str | None = None
    status: str | None = None
    nodes: int | None = None
    active_shards: int | None = None
    unassigned_shards: int | None = None

    indexes: list[IndexHealth] = Field(default_factory=list)


class IndexLag(BaseModel):
    index: str
    source: str
    database_rows: int = 0
    indexed_documents: int = 0
    # database_rows - indexed_documents. Positive means the index is behind;
    # negative means it holds documents the source no longer has, which is the
    # more dangerous direction -- a failed delete leaving a removed post
    # searchable.
    drift: int = 0
    in_sync: bool = True


class IngestLag(BaseModel):
    """
    How far each index trails its source table.

    There is no ingest queue to report: indexing happens inline on the write
    that caused it and is best effort by design -- SearchService swallows its
    own failures so a search outage can never fail a user's write. Drift is
    therefore the only honest measure of lag, and the rebuild script is what
    repairs it.
    """

    configured: bool = False
    reachable: bool = False
    error: str | None = None
    queued: int = 0
    queue_note: str | None = None
    indexes: list[IndexLag] = Field(default_factory=list)


class ReindexState(BaseModel):
    index: str
    status: str = "idle"  # idle | running | succeeded | failed
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    error: str | None = None
    triggered_by: str | None = None


class ReindexReport(BaseModel):
    indexes: list[ReindexState] = Field(default_factory=list)


class QueryHit(BaseModel):
    id: str
    score: float | None = None
    source: dict = Field(default_factory=dict)


class QueryResult(BaseModel):
    """
    Raw hits and scores behind a result.

    Deliberately unfiltered: this is the tester, so it shows what the index
    holds, not what the public endpoint would return. The public search path
    forces is_active on top of whatever it is asked, which is why a document
    can be visible here and unreachable there.
    """

    index: str
    query: str
    took_ms: int | None = None
    total: int = 0
    max_score: float | None = None
    hits: list[QueryHit] = Field(default_factory=list)
    error: str | None = None
    note: str | None = None


class FieldMapping(BaseModel):
    field: str
    type: str | None = None
    analyzer: str | None = None
    search_analyzer: str | None = None
    subfields: list[str] = Field(default_factory=list)


class IndexMapping(BaseModel):
    index: str
    physical: str | None = None
    fields: list[FieldMapping] = Field(default_factory=list)
    analyzers: dict = Field(default_factory=dict)
    tokenizers: dict = Field(default_factory=dict)
    # True when the live mapping no longer matches the one in
    # opensearch/indexes.py -- which means a rebuild is owed, because a
    # mapping is schema and cannot be changed in place.
    drifted: bool = False
    drift: list[str] = Field(default_factory=list)


class MappingReport(BaseModel):
    configured: bool = False
    reachable: bool = False
    error: str | None = None
    indexes: list[IndexMapping] = Field(default_factory=list)
