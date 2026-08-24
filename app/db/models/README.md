# Nexus SQLAlchemy Models

Split from the current `model.py` into domain-oriented modules.

## Structure

- `base.py` — SQLAlchemy declarative base
- `enums.py` — shared enums
- `users.py` — users and user preferences
- `colleges.py` — colleges
- `categories.py` — categories
- `posts.py` — posts and media
- `comments.py` — comments and edit logs
- `reactions.py` — post reactions
- `moderation.py` — moderation logs
- `chat.py` — chat rooms, participants and messages
- `support.py` — support conversations/messages
- `badges.py` — badges and campus ambassadors
- `activity.py` — activity logs
- `probabilities.py` — category probabilities
- `notifications.py` — notifications

## Comment improvements

`PostComment` now includes:

- `reply_count` for fast reply-count reads
- `updated_at`
- self-referencing `parent_id`
- explicit `parent` / `replies` relationships
- partial PostgreSQL indexes for:
  - root comments by `(post_id, created_at, id)`
  - replies by `(parent_id, created_at, id)`

The two partial indexes are PostgreSQL-specific. Generate/apply them through Alembic migrations in production.

## Import

```python
from app.models import Base, Post, PostComment, User
```

Replace `app` with your package name.
