from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import CollaborationRequestStatus, PostType
from app.domains.collaboration.redis import CollaborationRedis
from app.domains.collaboration.repository import CollaborationRepository
from app.domains.collaboration.schemas import CollabRequest
from app.domains.collaboration.storage import CollaborationStorage
from app.domains.post.repository import PostRepository
from app.domains.user.hydrate import attach_users

# A request may only move between these states, and only in this direction.
ALLOWED_TRANSITIONS: dict[CollaborationRequestStatus, set[CollaborationRequestStatus]] = {
    CollaborationRequestStatus.requested: {
        CollaborationRequestStatus.accepted,
        CollaborationRequestStatus.rejected,
        CollaborationRequestStatus.revoked,
    },
    CollaborationRequestStatus.accepted: {
        CollaborationRequestStatus.revoked,
    },
    # A rejected request is final; a revoked one may be sent again.
    CollaborationRequestStatus.rejected: set(),
    CollaborationRequestStatus.revoked: {
        CollaborationRequestStatus.requested,
    },
}


def _conflict(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"code": code, "message": message},
    )


class CollabStatusService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = CollaborationStorage(db)

    async def get_statuses(self, post_ids: list[UUID | str], user_id: UUID | str):
        return await self.storage.get_statuses(post_ids, user_id)


class CollaborationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CollaborationRepository(db)
        self.redis_store = CollaborationRedis()
        self.storage = CollaborationStorage(db)
        self.post_repo = PostRepository(db)

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    async def _get_collab_post(self, post_id: UUID | str):
        post = await self.post_repo.get_by_id(post_id)

        if not post:
            raise HTTPException(
                status_code=404,
                detail={"code": "post_not_found", "message": "Post not found"},
            )

        if post.type != PostType.collaboration:
            raise _conflict(
                "not_a_collaboration",
                "This post is not open for collaboration",
            )

        return post

    def _check_college_restriction(self, post, user_college_id: UUID | None) -> None:
        """A collaboration may be limited to one college."""
        restricted_to = post.restricted_to_college_id

        if restricted_to is not None and restricted_to != user_college_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "college_restricted",
                    "message": "This collaboration is not open to all colleges",
                },
            )

    @staticmethod
    def _require_self(actor_id: UUID | str, sender_id: UUID | str | None) -> None:
        """
        A request may only be sent or withdrawn by the person it belongs to.
        The caller states the sender explicitly and it has to match the
        authenticated user.
        """
        if sender_id is not None and sender_id != actor_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "sender_mismatch",
                    "message": "You can only send or withdraw your own collaboration requests",
                },
            )

    def _check_transition(
        self,
        current: CollaborationRequestStatus | None,
        target: CollaborationRequestStatus,
    ) -> None:
        if current is None:
            return

        current = CollaborationRequestStatus(current)

        if target not in ALLOWED_TRANSITIONS[current]:
            raise _conflict(
                "invalid_transition",
                f"A {current.value} request cannot become {target.value}",
            )

    async def _apply(
        self,
        post_id: UUID | str,
        sender_id: UUID | str,
        recipient_id: UUID | str,
        status: CollaborationRequestStatus,
        note: str | None = None,
        admin_note: str | None = None,
        reviewed: bool = False,
    ):
        request = await self.repo.upsert_status(
            post_id=post_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            status=status.value,
            note=note,
            admin_note=admin_note,
            reviewed_at=datetime.now(timezone.utc) if reviewed else None,
            commit=True,
        )

        # The sender's cached view of "which posts have I asked to join".
        await self.storage.set_status(sender_id, post_id, status.value)

        return request

    @staticmethod
    def _result(request) -> dict:
        return {
            "status": "success",
            "request_id": request.id,
            "post_id": request.post_id,
            "sender_id": request.sender_id,
            "recipient_id": request.recipient_id,
            "collab_status": request.status,
        }

    # ------------------------------------------------------------------
    # Requester side
    # ------------------------------------------------------------------

    async def send_request(
        self,
        post_id: UUID | str,
        actor_id: UUID | str,
        sender_college_id: UUID | None = None,
        note: str | None = None,
        sender_id: UUID | str | None = None,
    ):
        self._require_self(actor_id, sender_id)
        sender_id = actor_id

        post = await self._get_collab_post(post_id)

        if post.user_id == sender_id:
            raise _conflict(
                "own_post",
                "You cannot ask to join your own collaboration",
            )

        self._check_college_restriction(post, sender_college_id)

        existing = await self.repo.get_request(post_id, sender_id)

        if existing and existing.status == CollaborationRequestStatus.requested:
            raise _conflict(
                "already_requested",
                "You have already asked to join this collaboration",
            )

        if existing and existing.status == CollaborationRequestStatus.accepted:
            raise _conflict(
                "already_accepted",
                "You are already part of this collaboration",
            )

        self._check_transition(
            existing.status if existing else None,
            CollaborationRequestStatus.requested,
        )

        request = await self._apply(
            post_id,
            sender_id,
            post.user_id,
            CollaborationRequestStatus.requested,
            note=note,
        )

        return self._result(request)

    async def revoke_request(
        self,
        post_id: UUID | str,
        actor_id: UUID | str,
        sender_id: UUID | str | None = None,
    ):
        self._require_self(actor_id, sender_id)
        sender_id = actor_id

        existing = await self.repo.get_request(post_id, sender_id)

        if not existing:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "request_not_found",
                    "message": "You have not asked to join this collaboration",
                },
            )

        self._check_transition(
            existing.status,
            CollaborationRequestStatus.revoked,
        )

        request = await self._apply(
            post_id,
            sender_id,
            existing.recipient_id,
            CollaborationRequestStatus.revoked,
        )

        # Someone who walks away loses their seat in the chat room.
        from app.domains.chats.service import ChatService

        await ChatService(self.db).remove_participant(post_id, sender_id)

        return self._result(request)

    async def list_sent_requests(
        self,
        sender_id: UUID,
        status: CollaborationRequestStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollabRequest]:
        """Requests this user sent to other people's collaborations."""
        rows = await self.repo.list_sent(
            sender_id=sender_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return await attach_users(
            self.db,
            [CollabRequest.model_validate(r) for r in rows],
            ("sender_id", "sender"),
            ("recipient_id", "recipient"),
        )

    async def list_received_requests(
        self,
        recipient_id: UUID,
        status: CollaborationRequestStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollabRequest]:
        """Requests other people sent to this user's collaborations."""
        rows = await self.repo.list_received(
            recipient_id=recipient_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return await attach_users(
            self.db,
            [CollabRequest.model_validate(r) for r in rows],
            ("sender_id", "sender"),
            ("recipient_id", "recipient"),
        )

    # ------------------------------------------------------------------
    # Post author side
    # ------------------------------------------------------------------

    async def _require_post_author(self, post_id: UUID | str, user_id: UUID):
        post = await self._get_collab_post(post_id)

        if post.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "not_post_author",
                    "message": "Only the author of the post can review requests",
                },
            )

        return post

    async def list_requests(
        self,
        post_id: UUID,
        author_id: UUID,
        status: CollaborationRequestStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollabRequest]:
        await self._require_post_author(post_id, author_id)

        rows = await self.repo.list_by_post(
            post_id=post_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return await attach_users(
            self.db,
            [CollabRequest.model_validate(r) for r in rows],
            ("sender_id", "sender"),
            ("recipient_id", "recipient"),
        )

    async def review_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        accept: bool,
        note: str | None = None,
    ):
        """
        Accept or reject one request, addressed by its own id.

        Only the recipient — the author of the post — may decide.
        """
        request = await self.repo.get_by_id(request_id)

        if not request:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "request_not_found",
                    "message": "No such collaboration request",
                },
            )

        if request.recipient_id != reviewer_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "not_recipient",
                    "message": "Only the person this request was sent to can decide it",
                },
            )

        target = (
            CollaborationRequestStatus.accepted
            if accept
            else CollaborationRequestStatus.rejected
        )

        self._check_transition(request.status, target)

        updated = await self._apply(
            request.post_id,
            request.sender_id,
            request.recipient_id,
            target,
            admin_note=note,
            reviewed=True,
        )

        # Accepting is what actually puts someone in the room.
        if accept:
            from app.domains.chats.service import ChatService

            await ChatService(self.db).add_participant(
                request.post_id, request.sender_id
            )

        return self._result(updated)

    async def update_status(
        self,
        post_id: UUID | str,
        sender_id: UUID | str,
        recipient_id: UUID | str,
        status: CollaborationRequestStatus,
    ):
        """Unconditional status write, for internal callers."""
        request = await self._apply(post_id, sender_id, recipient_id, status)
        return self._result(request)

    # ------------------------------------------------------------------
    # Redis rebuild
    # ------------------------------------------------------------------

    async def build(self):
        from sqlalchemy import select

        from app.db.models import CollaborationRequest

        print("Starting Collaboration Redis build...")
        result = await self.db.execute(
            select(
                CollaborationRequest.post_id,
                CollaborationRequest.sender_id,
                CollaborationRequest.status,
            )
        )
        all_requests = result.fetchall()

        collabs_by_user: dict[str, dict[str, str]] = {}
        for post_id, sender_id, status in all_requests:
            val = status.value if hasattr(status, "value") else status
            collabs_by_user.setdefault(str(sender_id), {})[str(post_id)] = val

        pipeline = self.redis_store.redis.pipeline()
        for user_id, mapping in collabs_by_user.items():
            key = self.redis_store._key(user_id)
            temp_key = f"{key}:tmp"
            if mapping:
                pipeline.hset(temp_key, mapping=mapping)
            pipeline.rename(temp_key, key)

        await pipeline.execute()
        print(
            f"Collaboration Redis build completed. Restored {len(all_requests)} "
            f"collab statuses across {len(collabs_by_user)} users."
        )
