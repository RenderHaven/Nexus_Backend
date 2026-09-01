"""
Moderation audit trail.

For now every entry is written to the application log. The moderation_logs
table already exists, so persisting these is a matter of filling in _record
without touching any of the call sites.
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

    async def _record(self, event: str, **fields: Any) -> None:
        try:
            logger.info(
                "moderation.%s %s",
                event,
                " ".join(f"{k}={v}" for k, v in fields.items() if v is not None),
            )
            # TODO: persist to moderation_logs once the audit UI needs history.
        except Exception:
            logger.exception("Failed to record moderation event %s", event)

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
            status=moderation_status.value,
            action=getattr(STATUS_ACTIONS.get(moderation_status), "value", None),
            note=note,
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
            action=ModerationAction.remove.value,
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
