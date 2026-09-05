"""
Monitoring for the search cluster.

Search is the one piece of infrastructure the app is built to survive losing:
OPENSEARCH_URL is optional, indexing is best effort, and every write swallows
its own indexing failure rather than failing the user. That makes drift the
normal state rather than an alarm, and makes this screen the only place anyone
would notice it -- so what it reports has to be the truth about how far behind
the index is, not a green light.

Same three rules as the other infrastructure services (see
INFRA_MONITORING.md): bounded work, degrade rather than raise, read-only
except where the caller explicitly asked for a write. Here the one write is
the reindex, which runs in the background rather than inside the request.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import text

from app.domains.search.opensearch.admin import current_version
from app.domains.search.opensearch.client import get_opensearch, is_configured
from app.domains.search.opensearch.indexes import MAPPINGS, SearchIndexes
from app.domains.search.opensearch.schemas import (
    FieldMapping,
    IndexHealth,
    IndexLag,
    IndexMapping,
    IngestLag,
    MappingReport,
    QueryHit,
    QueryResult,
    ReindexReport,
    ReindexState,
    SearchHealth,
)
from app.redis.client import get_redis

logger = logging.getLogger(__name__)

# Hits returned by the query tester. It is a tester, not an export.
MAX_TEST_HITS = 50

# How long a finished reindex's outcome stays readable. Long enough that
# someone who triggered one and walked away still sees how it went.
REINDEX_STATE_TTL = 7 * 24 * 60 * 60

# Which source table each index is built from, and the rule that decides which
# of its rows are indexed at all. Mirrors _sources() in the rebuild script --
# only publicly visible posts and live accounts go in.
SOURCES: dict[str, tuple[str, str]] = {
    SearchIndexes.POSTS: ("posts", "is_active = true"),
    SearchIndexes.USERS: ("users", "is_active = true"),
    SearchIndexes.COLLEGES: ("colleges", "true"),
}


class SearchMonitorService:
    def __init__(self, db=None):
        self.db = db
        self.redis = get_redis()

    # ------------------------------------------------------------------
    # Index health
    # ------------------------------------------------------------------

    async def health(self) -> SearchHealth:
        if not is_configured():
            return SearchHealth(
                configured=False,
                reachable=False,
                error=(
                    "OPENSEARCH_URL is not set. Search is switched off in this "
                    "environment; every other route works without it."
                ),
            )

        client = get_opensearch()

        try:
            cluster = await client.cluster.health()
            info = await client.info()
        except Exception as exc:
            return SearchHealth(
                configured=True,
                reachable=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        report = SearchHealth(
            configured=True,
            reachable=True,
            cluster_name=cluster.get("cluster_name"),
            version=(info.get("version") or {}).get("number"),
            status=cluster.get("status"),
            nodes=cluster.get("number_of_nodes"),
            active_shards=cluster.get("active_shards"),
            unassigned_shards=cluster.get("unassigned_shards"),
        )

        for name in SearchIndexes.ALL:
            report.indexes.append(await self._index_health(client, name))

        return report

    async def _index_health(self, client, name: str) -> IndexHealth:
        alias = SearchIndexes.alias(name)
        row = IndexHealth(name=name, alias=alias)

        try:
            row.version = await current_version(name)
        except Exception:
            row.version = None

        if row.version is None:
            # No alias yet: the index has never been built. Not an error --
            # it is what an empty cluster looks like before the first rebuild.
            return row

        row.physical = SearchIndexes.physical(name, row.version)

        try:
            stats = await client.indices.stats(index=row.physical)
            primaries = stats["indices"][row.physical]["primaries"]
            row.exists = True
            row.documents = primaries["docs"]["count"]
            row.deleted_documents = primaries["docs"]["deleted"]
            row.size_bytes = primaries["store"]["size_in_bytes"]
        except Exception:
            row.exists = False

        try:
            health = await client.cluster.health(index=row.physical)
            row.status = health.get("status")
            row.shards = health.get("active_primary_shards")
            row.unassigned_shards = health.get("unassigned_shards")
        except Exception:
            pass

        try:
            settings = await client.indices.get_settings(index=row.physical)
            index_settings = settings[row.physical]["settings"]["index"]
            row.replicas = int(index_settings.get("number_of_replicas", 0))
        except Exception:
            pass

        return row

    # ------------------------------------------------------------------
    # Ingest lag
    # ------------------------------------------------------------------

    async def ingest_lag(self) -> IngestLag:
        """
        Source row count against indexed document count, per index.

        Counting is exact here rather than estimated: these are three counts
        over indexed boolean columns, and the whole point of the panel is that
        the two numbers can be compared, which an estimate would break.
        """
        queue_note = (
            "There is no ingest queue. Indexing happens inline on the write "
            "that caused it and is best effort -- a failure is logged and "
            "swallowed so it cannot fail the user's write. Drift is repaired "
            "by a reindex."
        )

        if not is_configured():
            return IngestLag(
                configured=False,
                reachable=False,
                queue_note=queue_note,
                error="OPENSEARCH_URL is not set.",
            )

        if self.db is None:
            return IngestLag(
                configured=True,
                reachable=False,
                queue_note=queue_note,
                error="No database session; ingest lag needs both sides to compare.",
            )

        client = get_opensearch()
        report = IngestLag(configured=True, reachable=True, queue_note=queue_note)

        for name, (table, condition) in SOURCES.items():
            row = IndexLag(index=name, source=table)

            try:
                row.database_rows = int(
                    (
                        await self.db.execute(
                            text(f"SELECT count(*) FROM {table} WHERE {condition}")
                        )
                    ).scalar_one()
                )
            except Exception as exc:
                report.error = f"{type(exc).__name__}: {exc}"

            try:
                alias = SearchIndexes.alias(name)
                if await client.indices.exists(index=alias):
                    row.indexed_documents = int(
                        (await client.count(index=alias))["count"]
                    )
            except Exception as exc:
                report.error = f"{type(exc).__name__}: {exc}"

            row.drift = row.database_rows - row.indexed_documents
            row.in_sync = row.drift == 0
            report.indexes.append(row)

        return report

    # ------------------------------------------------------------------
    # Reindex
    # ------------------------------------------------------------------

    def _state_key(self, name: str) -> str:
        return f"infra:reindex:{name}"

    async def reindex_status(self) -> ReindexReport:
        keys = [self._state_key(name) for name in SearchIndexes.ALL]

        try:
            values = await self.redis.mget(keys)
        except Exception:
            values = [None] * len(keys)

        states = []
        for name, raw in zip(SearchIndexes.ALL, values):
            if not raw:
                states.append(ReindexState(index=name))
                continue
            try:
                states.append(ReindexState(**json.loads(raw)))
            except Exception:
                states.append(ReindexState(index=name))

        return ReindexReport(indexes=states)

    async def _write_state(self, state: ReindexState) -> None:
        try:
            await self.redis.set(
                self._state_key(state.index),
                state.model_dump_json(),
                ex=REINDEX_STATE_TTL,
            )
        except Exception:
            logger.exception("could not record reindex state for %s", state.index)

    async def start_reindex(self, name: str, triggered_by: str | None = None) -> ReindexState:
        """
        Rebuild one index from Postgres, in the background.

        Not run inside the request: a full rebuild walks every row of the
        source table, which is minutes on a real dataset and far past any
        sensible HTTP timeout. The caller gets the state back immediately and
        polls.

        A rebuild is safe to trigger while search is live. The script fills a
        fresh version alongside the current one and only swaps the alias once
        the new index holds everything that was read, so a rebuild that fails
        halfway leaves search exactly as it was.
        """
        if name not in SearchIndexes.ALL:
            raise ValueError(
                f"Unknown index: {name}. Choose from {', '.join(SearchIndexes.ALL)}"
            )

        if not is_configured():
            raise ValueError("OPENSEARCH_URL is not set; there is nothing to rebuild.")

        current = (await self.reindex_status()).indexes
        existing = next((s for s in current if s.index == name), None)

        if existing and existing.status == "running":
            raise ValueError(f"A rebuild of {name} is already running.")

        state = ReindexState(
            index=name,
            status="running",
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
        )
        await self._write_state(state)

        asyncio.create_task(self._run_reindex(state))

        return state

    async def _run_reindex(self, state: ReindexState) -> None:
        """
        The background half.

        Opens its own session: the request's is closed by the time this runs.
        Calls rebuild_index rather than rebuild_all, because rebuild_all closes
        the shared OpenSearch client in its finally -- correct for a CLI
        script, and would pull the client out from under live requests here.
        """
        from app.db.session import SessionLocal
        from app.domains.search.scripts.rebuild_search import rebuild_index

        started = time.perf_counter()

        try:
            async with SessionLocal() as db:
                ok = await rebuild_index(db, state.index)

            state.status = "succeeded" if ok else "failed"
            if not ok:
                state.error = (
                    "The new index did not hold every row that was read, so the "
                    "alias was left pointing at the previous version. See the "
                    "server log for the counts."
                )
        except Exception as exc:
            logger.exception("reindex of %s failed", state.index)
            state.status = "failed"
            state.error = f"{type(exc).__name__}: {exc}"

        state.finished_at = datetime.now(timezone.utc)
        state.duration_seconds = round(time.perf_counter() - started, 3)
        await self._write_state(state)

    # ------------------------------------------------------------------
    # Query tester
    # ------------------------------------------------------------------

    async def run_query(
        self,
        index: str,
        query: str,
        size: int = 10,
    ) -> QueryResult:
        """
        Run a query against one index and hand back the raw hits and scores.

        A multi_match over the index's own text fields -- the same shape the
        real search uses -- rather than an arbitrary query body, so nothing a
        caller sends is interpreted as a query DSL. `size` is capped.
        """
        result = QueryResult(
            index=index,
            query=query,
            note=(
                "Unfiltered. The public search endpoint forces is_active on top "
                "of this, so a document visible here can still be unreachable "
                "there."
            ),
        )

        if index not in SearchIndexes.ALL:
            result.error = (
                f"Unknown index: {index}. Choose from {', '.join(SearchIndexes.ALL)}"
            )
            return result

        if not is_configured():
            result.error = "OPENSEARCH_URL is not set."
            return result

        fields = self._text_fields(index)
        size = max(1, min(size, MAX_TEST_HITS))

        try:
            response = await get_opensearch().search(
                index=SearchIndexes.alias(index),
                body={
                    "size": size,
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": fields,
                            "fuzziness": "AUTO",
                        }
                    },
                },
            )
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            return result

        hits = response.get("hits", {})
        total = hits.get("total", {})

        result.took_ms = response.get("took")
        result.total = total.get("value", 0) if isinstance(total, dict) else int(total)
        result.max_score = hits.get("max_score")
        result.hits = [
            QueryHit(
                id=hit.get("_id"),
                score=hit.get("_score"),
                source=hit.get("_source", {}),
            )
            for hit in hits.get("hits", [])
        ]

        return result

    @staticmethod
    def _text_fields(index: str) -> list[str]:
        """The searchable fields of an index, read off its mapping in source."""
        properties = MAPPINGS[index]["mappings"]["properties"]
        fields = [
            name
            for name, definition in properties.items()
            if definition.get("type") == "text"
        ]
        return fields or ["*"]

    # ------------------------------------------------------------------
    # Mappings and analyzers
    # ------------------------------------------------------------------

    async def mappings(self) -> MappingReport:
        """
        What each field is indexed as, and how text is tokenised.

        The live mapping is compared against the one in indexes.py, and any
        difference is flagged. That comparison is the point of the panel: a
        mapping is schema, it cannot be changed in place, so a drift means a
        rebuild is owed and search is quietly answering with the old rules
        until someone runs one.
        """
        if not is_configured():
            return MappingReport(
                configured=False,
                reachable=False,
                error="OPENSEARCH_URL is not set.",
            )

        client = get_opensearch()
        report = MappingReport(configured=True, reachable=True)

        for name in SearchIndexes.ALL:
            entry = IndexMapping(index=name)

            try:
                version = await current_version(name)
            except Exception as exc:
                report.error = f"{type(exc).__name__}: {exc}"
                report.indexes.append(entry)
                continue

            if version is None:
                entry.drift = ["not built yet"]
                entry.drifted = True
                report.indexes.append(entry)
                continue

            physical = SearchIndexes.physical(name, version)
            entry.physical = physical

            try:
                live = (await client.indices.get_mapping(index=physical))[physical]
                properties = live["mappings"].get("properties", {})

                settings = (await client.indices.get_settings(index=physical))[
                    physical
                ]["settings"]["index"]
                analysis = settings.get("analysis", {})
                entry.analyzers = analysis.get("analyzer", {})
                entry.tokenizers = analysis.get("tokenizer", {})
            except Exception as exc:
                report.error = f"{type(exc).__name__}: {exc}"
                report.indexes.append(entry)
                continue

            entry.fields = [
                FieldMapping(
                    field=field,
                    type=definition.get("type"),
                    analyzer=definition.get("analyzer"),
                    search_analyzer=definition.get("search_analyzer"),
                    subfields=sorted((definition.get("fields") or {}).keys()),
                )
                for field, definition in sorted(properties.items())
            ]

            entry.drift = self._mapping_drift(
                MAPPINGS[name]["mappings"]["properties"], properties
            )
            entry.drifted = bool(entry.drift)

            report.indexes.append(entry)

        return report

    @staticmethod
    def _mapping_drift(expected: dict, live: dict) -> list[str]:
        """
        Where the live mapping and the one in source disagree.

        Only the fields declared in source are checked, and only their type and
        analyzers. OpenSearch fills in defaults that were never written down,
        so comparing the two dicts wholesale would report drift on every index
        forever.
        """
        drift = []

        for field, definition in expected.items():
            actual = live.get(field)

            if actual is None:
                drift.append(f"{field}: missing from the live index")
                continue

            for key in ("type", "analyzer", "search_analyzer"):
                want = definition.get(key)
                got = actual.get(key)
                if want is not None and want != got:
                    drift.append(f"{field}.{key}: expected {want!r}, live has {got!r}")

        for field in live:
            if field not in expected:
                drift.append(f"{field}: in the live index but not in indexes.py")

        return drift
