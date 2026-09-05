"""
Index names and mappings.

A mapping is schema: it decides how text is tokenised and what can be filtered
or sorted on, and changing one needs a rebuild. It lives in source next to the
Alembic migrations for the same reason they do.

Nothing writes to a physical index by name. Every read and write goes through
an alias, so a rebuild can fill a fresh version alongside the live one and swap
the alias over in a single atomic step.
"""

from app.config import settings


class SearchIndexes:

    POSTS = "posts"
    USERS = "users"
    COLLEGES = "colleges"

    ALL = (POSTS, USERS, COLLEGES)

    @staticmethod
    def alias(name: str) -> str:
        """The name everything queries and indexes through."""
        return f"{settings.OPENSEARCH_INDEX_PREFIX}{name}"

    @staticmethod
    def physical(name: str, version: int) -> str:
        """A concrete index behind the alias, e.g. `posts_v2`."""
        return f"{settings.OPENSEARCH_INDEX_PREFIX}{name}_v{version}"


# Usernames are matched by prefix as the user types, so they are indexed as
# edge n-grams. The query itself is not n-grammed -- searching "vik" should hit
# "vikram", not every user sharing a two-letter prefix with it.
_USERNAME_ANALYSIS = {
    "tokenizer": {
        "username_edge": {
            "type": "edge_ngram",
            "min_gram": 2,
            "max_gram": 20,
            "token_chars": ["letter", "digit"],
        }
    },
    "analyzer": {
        "username_index": {
            "type": "custom",
            "tokenizer": "username_edge",
            "filter": ["lowercase"],
        },
        "username_search": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": ["lowercase"],
        },
    },
}

_USERNAME_FIELD = {
    "type": "text",
    "analyzer": "username_index",
    "search_analyzer": "username_search",
    "fields": {"kw": {"type": "keyword"}},
}


# Only what is matched, filtered, sorted or ranked on belongs in a mapping.
# Display fields (avatars, xp, counts) are hydrated from the entity cache after
# the search returns ids, so adding one never costs a reindex.
MAPPINGS: dict[str, dict] = {
    SearchIndexes.POSTS: {
        "settings": {
            "index": {"number_of_shards": 1, "number_of_replicas": 0},
        },
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "english"},
                "content": {"type": "text", "analyzer": "english"},
                # No author_username: nothing about a user is denormalised
                # into a post, so a rename never has to fan out here. The
                # trade is that a post cannot be found by its author's name --
                # search the users index for that.
                "user_id": {"type": "keyword"},
                "college_id": {"type": "keyword"},
                "category_id": {"type": "keyword"},
                "type": {"type": "keyword"},
                # Only active posts are indexed at all, so this is true for
                # every document here. It is kept, and filtered on at query
                # time, as a second line of defence: if a delete ever fails
                # and leaves a stale document behind, the filter still hides
                # it from readers.
                "is_active": {"type": "boolean"},
                "created_at": {"type": "date"},
                "engagement_score": {"type": "float"},
            }
        },
    },
    SearchIndexes.USERS: {
        "settings": {
            "index": {"number_of_shards": 1, "number_of_replicas": 0},
            "analysis": _USERNAME_ANALYSIS,
        },
        "mappings": {
            "properties": {
                "username": _USERNAME_FIELD,
                "college_id": {"type": "keyword"},
                "role": {"type": "keyword"},
                "is_alumni": {"type": "boolean"},
                "created_at": {"type": "date"},
            }
        },
    },
    SearchIndexes.COLLEGES: {
        "settings": {
            "index": {"number_of_shards": 1, "number_of_replicas": 0},
        },
        "mappings": {
            "properties": {
                "name": {
                    "type": "text",
                    "fields": {"kw": {"type": "keyword"}},
                },
                "tagline": {"type": "text"},
                "location": {
                    "type": "text",
                    "fields": {"kw": {"type": "keyword"}},
                },
            }
        },
    },
}
