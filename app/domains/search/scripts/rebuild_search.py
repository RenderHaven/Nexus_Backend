"""
Rebuild the search indices from Postgres.

Live indexing (SearchService.update_*_search) is best effort by design: it
swallows and logs its own failures so a search outage can never fail a user's
write. This script is the other half of that decision -- the thing that
repairs the drift, and the only way rows that existed before indexing was
switched on ever reach the index.

Run it:

  * once, to backfill an empty cluster
  * after any change to a mapping in opensearch/indexes.py
  * on a schedule, so every swallowed write failure self-heals

Nothing is rebuilt in place. Each run fills a fresh version of the index while
the live one keeps serving, and only swaps the alias once the new version is
complete -- so a failed rebuild leaves search exactly as it was.

    python -m app.domains.search.scripts.rebuild_search
    python -m app.domains.search.scripts.rebuild_search posts
    python -m app.domains.search.scripts.rebuild_search --keep-old
"""

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.session import engine
from app.domains.colleges.repository import CollegeRepository
from app.domains.post.repository import PostRepository
from app.domains.search.documents import (
    bulk_body,
    college_document,
    post_document,
    user_document,
)
from app.domains.search.opensearch import (
    SearchIndexes,
    close_opensearch,
    get_opensearch,
    is_configured,
)
from app.domains.search.opensearch.admin import (
    create_index,
    current_version,
    drop_index,
    swap_alias,
)
from app.domains.user.repository import UserRepository

logger = logging.getLogger(__name__)

# Rows per database page and per _bulk request. Large enough that the round
# trips disappear, small enough that a page stays well inside OpenSearch's
# default 100MB request cap.
BATCH = 500


def _sources(db):
    """index name -> (page fetcher, document builder).

    Each fetcher is the domain repository's own bulk read, so the SQL behind a
    rebuild is the same SQL the domain uses everywhere else.
    """
    post_repo = PostRepository(db)
    user_repo = UserRepository(db)

    async def active_posts(after=None, limit=1000):
        # Only publicly visible posts go in the index -- the same rule
        # update_post_search applies one document at a time.
        return await post_repo.get_all_posts(after=after, limit=limit, is_active=True)

    async def active_users(after=None, limit=1000):
        # Deactivated accounts are out of the index, same as their posts.
        return await user_repo.get_all_users(after=after, limit=limit, is_active=True)

    return {
        SearchIndexes.POSTS: (active_posts, post_document),
        SearchIndexes.USERS: (active_users, user_document),
        SearchIndexes.COLLEGES: (
            CollegeRepository(db).get_all_colleges,
            college_document,
        ),
    }


async def _fill(physical: str, fetch_page, build_doc) -> int:
    """Walk every row into one physical index. Returns the number indexed."""
    client = get_opensearch()
    after = None
    total = 0

    while True:
        rows = await fetch_page(after=after, limit=BATCH)
        if not rows:
            break

        response = await client.bulk(body=bulk_body(physical, rows, build_doc))

        if response.get("errors"):
            failed = [
                item["index"]
                for item in response.get("items", [])
                if item.get("index", {}).get("error")
            ]
            # Loud but not fatal: a handful of rejected documents should not
            # throw away a rebuild that is otherwise complete. The count check
            # in rebuild_index decides whether the result is good enough.
            logger.error(
                "%s: %d document(s) rejected, first: %s",
                physical,
                len(failed),
                failed[0].get("error") if failed else None,
            )

        total += len(rows)
        after = (rows[-1].created_at, rows[-1].id)
        print(f"  {physical}: {total} indexed")

    return total


async def rebuild_index(db, name: str, keep_old: bool = False) -> bool:
    """
    Build a new version of one index and move its alias onto it.

    The alias is only swapped if the new index actually holds what was read
    out of Postgres, so a rebuild that dies halfway leaves the previous
    version serving.
    """
    fetch_page, build_doc = _sources(db)[name]

    old = await current_version(name)
    new = (old or 0) + 1

    physical = await create_index(name, new)
    print(f"{name}: building {physical} (live: {'v' + str(old) if old else 'none'})")

    expected = await _fill(physical, fetch_page, build_doc)

    client = get_opensearch()
    await client.indices.refresh(index=physical)
    actual = (await client.count(index=physical))["count"]

    if actual != expected:
        logger.error(
            "%s: built %d document(s) but read %d row(s); leaving the alias "
            "where it is and keeping %s for inspection",
            name,
            actual,
            expected,
            physical,
        )
        return False

    await swap_alias(name, new)
    print(f"{name}: alias -> {physical} ({actual} docs)")

    if old is not None and not keep_old:
        await drop_index(name, old)

    return True


async def rebuild_all(only: list[str] | None = None, keep_old: bool = False) -> bool:
    if not is_configured():
        print("OPENSEARCH_URL is not set; nothing to rebuild")
        return False

    names = only or list(SearchIndexes.ALL)

    unknown = [n for n in names if n not in SearchIndexes.ALL]
    if unknown:
        print(f"unknown index(es): {', '.join(unknown)}")
        print(f"choose from: {', '.join(SearchIndexes.ALL)}")
        return False

    Session = async_sessionmaker(bind=engine, autocommit=False, autoflush=False)
    ok = True

    print("--- Starting search rebuild ---")
    try:
        async with Session() as db:
            for name in names:
                # One index failing must not stop the others: a broken posts
                # rebuild should still let users and colleges refresh.
                try:
                    ok &= await rebuild_index(db, name, keep_old=keep_old)
                except Exception:
                    logger.exception("%s: rebuild failed", name)
                    ok = False
    finally:
        await close_opensearch()

    print(f"--- Search rebuild {'complete' if ok else 'FINISHED WITH ERRORS'} ---")
    return ok


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args = sys.argv[1:]
    keep_old = "--keep-old" in args
    names = [a for a in args if not a.startswith("-")] or None

    return 0 if asyncio.run(rebuild_all(names, keep_old=keep_old)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
