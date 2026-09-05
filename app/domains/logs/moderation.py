"""
Moderation audit trail.

Every staff decision is written to moderation_logs and echoed to the
application log. The table is what GET /posts/{id}/moderation_history and the
admin activity feed read back.
"""
import logging
from typing import Any
from uuid import UUID

from app.db.models import ModerationAction, ModerationStatus

logger = logging.getLogger("moderation")

# How a moderation outcome maps onto the action recorded against it.
STATUS_ACTIONS: dict[ModerationStatus, ModerationAction] = {
    ModerationStatus.approved: ModerationAction.approve,
    ModerationStatus.hold: ModerationAction.hold,
    ModerationStatus.removed: ModerationAction.remove,
}


class ModerationLogService:
    """
    Records what moderators did. Never raises: a failure to write the audit
    trail must not fail the moderation action the user just performed.
    """

    def __init__(self, db=None):
        self.db = db

    async def _record(
        self,
        event: str,
        post_id: UUID,
        moderator_id: UUID,
        action: ModerationAction | None = None,
        note: str | None = None,
        **fields: Any,
    ) -> None:
        """
        Write one audit row. Swallows everything: losing the audit trail is
        bad, but failing the moderation action the user just performed
        because the audit write failed is worse.
        """
        try:
            logger.info(
                "moderation.%s post_id=%s moderator_id=%s %s",
                event,
                post_id,
                moderator_id,
                " ".join(f"{k}={v}" for k, v in fields.items() if v is not None),
            )
        except Exception:
            logger.exception("Failed to log moderation event %s", event)

        if self.db is None or action is None:
            # No session (or no action worth recording, e.g. a status with no
            # ModerationAction of its own) -- the stdout line above is all
            # this event gets.
            return

        try:
            from app.domains.logs.repository import ModerationLogRepository

            await ModerationLogRepository(self.db).add(
                post_id=post_id,
                coach_id=moderator_id,
                action=action,
                note=note,
            )
        except Exception:
            logger.exception(
                "Failed to persist moderation event %s for post %s",
                event,
                post_id,
            )

    async def log_review(
        self,
        post_id: UUID,
        moderator_id: UUID,
        moderation_status: ModerationStatus,
        note: str | None = None,
    ) -> None:
        """A moderator approved, held or removed a post."""
        await self._record(
            "review",
            post_id=post_id,
            moderator_id=moderator_id,
            action=STATUS_ACTIONS.get(moderation_status),
            note=note,
            status=moderation_status.value,
        )

    async def log_permanent_delete(
        self,
        post_id: UUID,
        moderator_id: UUID,
        note: str | None = None,
    ) -> None:
        """A moderator removed a post from the platform for good."""
        await self._record(
            "permanent_delete",
            post_id=post_id,
            moderator_id=moderator_id,
            action=ModerationAction.remove,
            note=note,
        )

    async def log_restricted_create(
        self,
        post_id: UUID,
        moderator_id: UUID,
        post_type: str,
    ) -> None:
        """A moderator created a post type ordinary users cannot."""
        await self._record(
            "restricted_create",
            post_id=post_id,
            moderator_id=moderator_id,
            post_type=post_type,
        )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def history_for_post(self, post_id: UUID, limit: int = 50, offset: int = 0):
        """Every recorded decision on one post, newest first."""
        if self.db is None:
            return []

        from app.domains.logs.repository import ModerationLogRepository

        return await ModerationLogRepository(self.db).list_for_post(
            post_id=post_id,
            limit=limit,
            offset=offset,
        )
