import json
from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys


class CommentsRedis:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, comment_id: UUID | str) -> str:
        return RedisKeys.comment(str(comment_id))

    def _replies_key(self, comment_id: UUID | str) -> str:
        return RedisKeys.comment_replies(str(comment_id))

    def _comments_key(self, post_id: UUID | str) -> str:
        return RedisKeys.post_comments(str(post_id))

    async def get_comment(self, comment_id: UUID | str) -> dict | None:
        data = await self.redis.get(self._key(comment_id))
        if data is None:
            return None
        return json.loads(data)

    async def set_comment(self, comment: dict | str, comment_data: dict | None = None) -> None:
        if isinstance(comment, dict):
            cdict = comment
        else:
            cdict = comment_data or {}
            if "id" not in cdict and comment:
                cdict["id"] = comment

        await self.redis.set(
            self._key(str(cdict["id"])),
            json.dumps(cdict),
        )

    async def get_many_comments(self, comment_ids: list[UUID | str]) -> list[dict | None]:
        if not comment_ids:
            return []

        keys = [self._key(str(cid)) for cid in comment_ids]
        raw_items = await self.redis.mget(keys)

        results = []
        for item in raw_items:
            if item is not None:
                results.append(json.loads(item))
            else:
                results.append(None)

        return results

    async def set_many_comments(self, comments: list[dict]) -> None:
        if not comments:
            return

        mapping = {
            self._key(str(c["id"])): json.dumps(c)
            for c in comments
        }
        await self.redis.mset(mapping)

    async def delete_comment(self, comment_id: UUID | str) -> None:
        await self.redis.delete(self._key(comment_id))

    async def get_comments_ids(self, post_id: UUID | str) -> list[str] | None:
        data = await self.redis.get(self._comments_key(post_id))
        if data is None:
            return None
        return json.loads(data)

    async def set_comments_ids(self, post_id: UUID | str, comment_ids: list[str]) -> None:
        await self.redis.set(self._comments_key(post_id), json.dumps(comment_ids))

    async def prepend_comment_id(self, post_id: UUID | str, comment_id: UUID | str) -> None:
        ids = await self.get_comments_ids(post_id)
        if ids is not None:
            cid_str = str(comment_id)
            if cid_str in ids:
                ids.remove(cid_str)
            ids.insert(0, cid_str)  # Newest on top
            await self.set_comments_ids(post_id, ids)

    async def remove_comment_id(self, post_id: UUID | str, comment_id: UUID | str) -> None:
        ids = await self.get_comments_ids(post_id)
        if ids is not None:
            cid_str = str(comment_id)
            if cid_str in ids:
                ids.remove(cid_str)
                await self.set_comments_ids(post_id, ids)

    async def invalidate_comments_ids(self, post_id: UUID | str) -> None:
        await self.redis.delete(self._comments_key(post_id))

    async def get_replies_ids(self, comment_id: UUID | str) -> list[str] | None:
        data = await self.redis.get(self._replies_key(comment_id))
        if data is None:
            return None
        return json.loads(data)

    async def set_replies_ids(self, comment_id: UUID | str, reply_ids: list[str]) -> None:
        await self.redis.set(self._replies_key(comment_id), json.dumps(reply_ids))

    async def prepend_reply_id(self, parent_id: UUID | str, reply_id: UUID | str) -> None:
        ids = await self.get_replies_ids(parent_id)
        if ids is not None:
            rid_str = str(reply_id)
            if rid_str in ids:
                ids.remove(rid_str)
            ids.insert(0, rid_str)  # Newest on top
            await self.set_replies_ids(parent_id, ids)

    async def remove_reply_id(self, parent_id: UUID | str, reply_id: UUID | str) -> None:
        ids = await self.get_replies_ids(parent_id)
        if ids is not None:
            rid_str = str(reply_id)
            if rid_str in ids:
                ids.remove(rid_str)
                await self.set_replies_ids(parent_id, ids)

    async def invalidate_replies_ids(self, comment_id: UUID | str) -> None:
        await self.redis.delete(self._replies_key(comment_id))