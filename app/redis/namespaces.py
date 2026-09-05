"""
The key namespaces this app keeps in Redis.

One table, because every panel on the Cache Engine screen is a different
question about the same list: how many keys does each namespace hold, what is
its hit rate, what is it supposed to expire after, and what does invalidating
it drop. Adding a new cached thing means adding a row here -- nothing else in
the monitoring service needs to change.

Order matters. classify() takes the first pattern that matches, so a specific
namespace must come before the general one it sits inside: `user:profile:*`
before `user:*`, or every profile key would be counted as a user.
"""
from dataclasses import dataclass
from fnmatch import fnmatchcase

HOUR = 60 * 60
CACHE_TTL = 8 * HOUR


@dataclass(frozen=True)
class Namespace:
    name: str
    pattern: str
    label: str
    description: str
    # What the code writing these keys sets as the TTL. None means the keys
    # are written without one on purpose (or, for `cursor`, by accident -- the
    # service reports observed TTLs alongside this so the two can disagree
    # visibly rather than silently).
    ttl_seconds: int | None = None
    ttl_note: str | None = None
    # An entity cache: entity:{id} holding one row, bust-on-write. These are
    # the ones a hit rate actually means something for.
    is_entity_cache: bool = False


NAMESPACES: tuple[Namespace, ...] = (
    Namespace(
        name="user_profile",
        pattern="user:profile:*",
        label="User profiles",
        description="A user's full profile document, including the profile JSONB.",
        ttl_seconds=CACHE_TTL,
    ),
    Namespace(
        name="user_liked_posts",
        pattern="user:*:liked_posts",
        label="Liked posts",
        description="Set of post ids one person has liked. Drives is_liked on every card.",
        ttl_note="No expiry: it is the working copy of the like state, not a cache of it.",
    ),
    Namespace(
        name="user_collab_status",
        pattern="user:*:collab_status",
        label="Collab status",
        description="Which collaborations one person has asked to join.",
        ttl_note="No expiry, same reason as liked posts.",
    ),
    Namespace(
        name="user",
        pattern="user:*",
        label="Users",
        description="UserBasic per id. Every author, sender and moderator shown anywhere resolves here.",
        ttl_seconds=CACHE_TTL,
        is_entity_cache=True,
    ),
    Namespace(
        name="post_comments",
        pattern="post:*:comments",
        label="Post comment lists",
        description="Comment id lists per post.",
    ),
    Namespace(
        name="post",
        pattern="post:*",
        label="Posts",
        description="One post's own row. Carries ids only -- author, category and college are hydrated per read.",
        ttl_seconds=CACHE_TTL,
        is_entity_cache=True,
    ),
    Namespace(
        name="comment_replies",
        pattern="comments:replies:*",
        label="Comment replies",
        description="Reply id lists per comment.",
    ),
    Namespace(
        name="comment",
        pattern="comments:*",
        label="Comments",
        description="One comment's own row. The author is hydrated per read.",
        ttl_seconds=CACHE_TTL,
        is_entity_cache=True,
    ),
    Namespace(
        name="category_all",
        pattern="category:all",
        label="Category list",
        description="The whole category table, for GET /categories.",
        ttl_note="No expiry: invalidated on write, not by time.",
    ),
    Namespace(
        name="category",
        pattern="category:*",
        label="Categories",
        description="One category per id, for hydrating posts.",
        ttl_note="No expiry: the table is tiny and changes are rare.",
        is_entity_cache=True,
    ),
    Namespace(
        name="college",
        pattern="college:*",
        label="Colleges",
        description="One college per id. Busting this is what makes a rename correct everywhere.",
        ttl_seconds=CACHE_TTL,
        is_entity_cache=True,
    ),
    Namespace(
        name="pool_cursor",
        pattern="pool:cursor:*",
        label="Pool cursors",
        description="Saved position in a pool for one paginating client.",
    ),
    Namespace(
        name="pool_group_cursor",
        pattern="pool_group:cursor:*",
        label="Pool group cursors",
        description="Saved position across a group of pools.",
    ),
    Namespace(
        name="pool",
        pattern="pool:*",
        label="Pools",
        description="Ranked ZSETs behind the feed, the type tabs and the campus lists.",
        ttl_note="Per pool: a refreshing pool expires on its refresh time, an idle one on its idle age, and a permanent one never.",
    ),
    Namespace(
        name="cursor",
        pattern="cursor:*",
        label="Cursors",
        description="Opaque pagination cursors handed back to clients.",
        ttl_note="Written with no expiry, which means these accumulate. Watch the key count here.",
    ),
    Namespace(
        name="feed",
        pattern="feed:*",
        label="Feeds",
        description="Reserved by RedisKeys.feed; nothing writes it today.",
    ),
    Namespace(
        name="metrics",
        pattern="metrics:*",
        label="Cache metrics",
        description="The hit/miss counters behind this screen.",
        ttl_note="Hourly buckets expire after 25h; the running totals do not.",
    ),
)

BY_NAME: dict[str, Namespace] = {ns.name: ns for ns in NAMESPACES}

# Namespaces a hit rate is recorded for. Anything not listed still gets
# counted by key, it just has no read instrumentation.
ENTITY_CACHES: tuple[str, ...] = tuple(
    ns.name for ns in NAMESPACES if ns.is_entity_cache
)


def classify(key: str) -> str:
    """Which namespace a key belongs to. 'other' when nothing claims it."""
    for namespace in NAMESPACES:
        if fnmatchcase(key, namespace.pattern):
            return namespace.name
    return "other"
