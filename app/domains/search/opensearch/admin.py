"""
Index lifecycle: creating a version, pointing an alias at it, tearing it down.

Kept apart from the query and indexing paths because these are the operations
a rebuild script runs, not ones a request ever performs.
"""

import logging

from .client import get_opensearch
from .indexes import MAPPINGS, SearchIndexes

logger = logging.getLogger(__name__)


async def create_index(name: str, version: int) -> str:
    """Create one concrete version of an index with its mapping, and return
    the physical name. Safe to call on an index that already exists."""
    client = get_opensearch()
    physical = SearchIndexes.physical(name, version)

    if not await client.indices.exists(index=physical):
        await client.indices.create(index=physical, body=MAPPINGS[name])
        logger.info("created index %s", physical)

    return physical


async def swap_alias(name: str, to_version: int) -> None:
    """
    Point an alias at a new version and detach every older one, in a single
    atomic step. Readers never see the alias missing or pointing at two
    indices at once.
    """
    client = get_opensearch()
    alias = SearchIndexes.alias(name)
    target = SearchIndexes.physical(name, to_version)

    actions = [{"remove": {"index": f"{alias}_v*", "alias": alias}}]
    actions.append({"add": {"index": target, "alias": alias}})

    try:
        await client.indices.update_aliases(body={"actions": actions})
    except Exception:
        # `remove` fails when the alias does not exist yet, which is the
        # normal case on a first build. Add it on its own instead.
        await client.indices.update_aliases(
            body={"actions": [{"add": {"index": target, "alias": alias}}]}
        )

    logger.info("alias %s -> %s", alias, target)


async def current_version(name: str) -> int | None:
    """Which version an alias currently points at, or None if unbuilt."""
    client = get_opensearch()
    alias = SearchIndexes.alias(name)

    if not await client.indices.exists_alias(name=alias):
        return None

    info = await client.indices.get_alias(name=alias)
    for physical in info:
        _, _, suffix = physical.rpartition("_v")
        if suffix.isdigit():
            return int(suffix)

    return None


async def drop_index(name: str, version: int) -> None:
    client = get_opensearch()
    physical = SearchIndexes.physical(name, version)

    if await client.indices.exists(index=physical):
        await client.indices.delete(index=physical)
        logger.info("dropped index %s", physical)


async def ensure_all() -> None:
    """
    Make sure every index exists and has an alias, without reindexing.

    This is the "we just pointed at an empty cluster" path: it gets search
    answering queries (with nothing in it) rather than erroring. Filling the
    indices is the rebuild script's job.
    """
    for name in SearchIndexes.ALL:
        if await current_version(name) is None:
            await create_index(name, 1)
            await swap_alias(name, 1)
