"""
What each hand-written migration is supposed to have left behind.

There is no Alembic here. Migrations are scripts under `app/scripts/`, each
written to be safe to run more than once, and nothing records which of them
have run. So "which revision is applied" has no answer -- there is no revision
ledger to read.

What can be answered, and is more useful anyway, is whether each script's
*effect* is present in the live schema: does the column exist, does the index
exist, does the invariant hold. For idempotent scripts that is strictly better
than a bookkeeping table, because it reports the database as it actually is
rather than as some ledger claims it was left.

Adding a migration script means adding a row here. A script with no row shows
up as unknown rather than silently passing.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Migration:
    script: str
    title: str
    description: str
    # (table, column) pairs the script adds or renames into place.
    columns: tuple[tuple[str, str], ...] = ()
    # Index names the script creates.
    indexes: tuple[str, ...] = ()
    # A count query that must return 0 for the script's effect to hold. This
    # is how a data backfill is checked -- there is no schema change to look
    # for, only rows that should no longer exist.
    violations_sql: str | None = None
    violations_label: str | None = None


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        script="app/scripts/migrate_user_is_active.py",
        title="User deactivation",
        description=(
            "is_active and updated_at on users, plus the indexes the admin "
            "user table filters and sorts on."
        ),
        columns=(("users", "is_active"), ("users", "updated_at")),
        indexes=(
            "ix_users_is_active",
            "ix_users_college_role",
            "ix_users_username",
            "ix_users_created_at",
        ),
    ),
    Migration(
        script="app/scripts/migrate_post_media_public_id.py",
        title="Media public ids",
        description=(
            "public_id on post_media, so a takedown can move the file out of "
            "the live Cloudinary folder instead of only forgetting its URL."
        ),
        columns=(("post_media", "public_id"),),
    ),
    Migration(
        script="app/scripts/migrate_collab_sender_recipient.py",
        title="Collaboration sender/recipient",
        description=(
            "user_id renamed to sender_id and recipient_id added, so a request "
            "names both sides rather than implying one from the post."
        ),
        columns=(
            ("collaboration_requests", "sender_id"),
            ("collaboration_requests", "recipient_id"),
        ),
        indexes=("idx_collab_requests_sender", "idx_collab_requests_recipient"),
    ),
    Migration(
        script="app/scripts/migrate_moderation_indexes.py",
        title="Moderation queue indexes",
        description=(
            "The composite indexes behind the review queue and its audit "
            "trail. Without them every tab of that screen is a sequential scan."
        ),
        indexes=(
            "ix_posts_moderation_queue",
            "ix_posts_reviewed_at",
            "ix_posts_user_moderation",
            "ix_moderation_logs_post",
            "ix_moderation_logs_coach",
            "ix_moderation_logs_created_at",
        ),
    ),
    Migration(
        script="app/scripts/backfill_post_is_active.py",
        title="is_active invariant",
        description=(
            "A data backfill, not a schema change: posts.is_active must equal "
            "(published AND approved). Rows written before the rule was "
            "enforced can violate it."
        ),
        violations_sql=(
            "SELECT count(*) FROM posts WHERE is_active <> "
            "(status = 'published' AND moderation_status = 'approved')"
        ),
        violations_label="posts whose is_active disagrees with the rule",
    ),
)
