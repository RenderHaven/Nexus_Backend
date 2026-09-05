"""
The one helper every list endpoint uses to resolve the people it references.

A row carries ids, never a copy of the person. Whatever needs a name attaches
it here, in one batch against user:{id}, so a profile edit is one cache delete
rather than a hunt through every cached thing that embedded the old name.
"""
from typing import Sequence
from uuid import UUID


async def attach_users(db, items: Sequence, *fields: tuple[str, str]) -> Sequence:
    """
    Resolve one or more id fields on a list of models against user:{id}.

    Each `fields` entry is (id_attribute, target_attribute) -- so a comment is
    ("user_id", "author"), a message ("sender_id", "author"), and a
    collaboration request takes both ("sender_id", "sender") and
    ("recipient_id", "recipient"). Every field named goes into the same MGET,
    so a listing costs one Redis round trip no matter how many people it
    refers to.
    """
    if not items or not fields:
        return items

    from app.domains.user.service import UserService

    ids: list[UUID] = [
        user_id
        for item in items
        for id_attr, _ in fields
        if (user_id := getattr(item, id_attr, None)) is not None
    ]

    if not ids:
        return items

    users = await UserService(db).get_authors(ids)

    for item in items:
        for id_attr, target in fields:
            setattr(item, target, users.get(getattr(item, id_attr, None)))

    return items
