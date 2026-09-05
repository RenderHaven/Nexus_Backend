"""
Row -> index document.

Only what is matched, filtered, sorted or ranked on goes in. Display fields
are hydrated from the entity cache after a search returns ids, so this stays
narrow on purpose -- adding an avatar to UserBasic must never cost a reindex.

The row types here are the flat SELECTs in repository.py, not ORM objects: an
indexer should never trigger lazy loads.
"""

from typing import Any


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _enum(value) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))


def post_document(row) -> dict[str, Any]:
    return {
        "title": row.title,
        "content": row.content,
        "user_id": str(row.user_id),
        "college_id": str(row.college_id) if row.college_id else None,
        "category_id": str(row.category_id) if row.category_id else None,
        "type": _enum(row.type),
        "is_active": bool(row.is_active),
        "created_at": _iso(row.created_at),
        "engagement_score": float(row.engagement_score or 0.0),
    }


def user_document(row) -> dict[str, Any]:
    return {
        "username": row.username,
        "college_id": str(row.college_id) if row.college_id else None,
        "role": _enum(row.role),
        "is_alumni": bool(row.is_alumni),
        "created_at": _iso(row.created_at),
    }


def college_document(row) -> dict[str, Any]:
    return {
        "name": row.name,
        "tagline": row.tagline,
        "location": row.location,
    }


# name -> (document builder, index name)
BUILDERS = {
    "posts": post_document,
    "users": user_document,
    "colleges": college_document,
}


def bulk_body(index: str, rows, builder) -> list[dict]:
    """
    Flatten rows into an OpenSearch _bulk payload.

    `_id` is the row's primary key, so every write is an upsert and re-running
    a backfill can never duplicate a document.
    """
    body: list[dict] = []

    for row in rows:
        body.append({"index": {"_index": index, "_id": str(row.id)}})
        body.append(builder(row))

    return body
