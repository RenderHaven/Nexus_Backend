import os
import re

# Read original interaction repository
with open('app/domains/interaction/repository.py', 'r') as f:
    repo_content = f.read()

# Read original interaction service
with open('app/domains/interaction/service.py', 'r') as f:
    svc_content = f.read()

# Read api/posts.py
with open('app/api/posts.py', 'r') as f:
    api_content = f.read()

os.makedirs('app/domains/comment', exist_ok=True)

# 1. Create CommentRepository
comment_repo = """from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model import PostInteraction, InteractionType

class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, post_interaction_id: UUID) -> PostInteraction | None:
        return await self.db.get(PostInteraction, post_interaction_id)

    async def add_comment(self, post_id: UUID, user_id: UUID, comment: str):
        post_interaction = PostInteraction(
            post_id=post_id,
            user_id=user_id,
            type=InteractionType.comment,
            body=comment,
            is_active=True
        )
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction

    async def add_comment_reply(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        parent_post_interaction = await self.get_by_id(post_interaction_id)
        if not parent_post_interaction:
            raise Exception("Parent post interaction not found")
        post_id = parent_post_interaction.post_id
        if not parent_post_interaction.type == InteractionType.comment:
            raise Exception("Parent post interaction is not a comment")
        if not parent_post_interaction.is_active:
            raise Exception("Parent post interaction is not active")

        post_interaction = PostInteraction(
            post_id=post_id,
            user_id=user_id,
            body=comment,
            parent_id=post_interaction_id,
            type=InteractionType.comment,
            is_active=True
        )
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction

    async def edit_comment(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        post_interaction = await self.get_by_id(post_interaction_id)
        if not post_interaction:
            raise Exception("Post interaction not found")
        if not post_interaction.type == InteractionType.comment:
            raise Exception("Post interaction is not a comment")
        if not post_interaction.user_id == user_id:
            raise Exception("Post interaction is not owned by the user")
        if not post_interaction.is_active:
            raise Exception("Post interaction is not active")
        await self.delete(post_interaction_id)
        new_post_interaction = await self.add_comment(post_interaction.post_id, post_interaction.user_id, comment)
        return new_post_interaction

    async def delete(self, post_interaction_id: UUID) -> bool:
        await self.db.execute(
            update(PostInteraction)
            .where(PostInteraction.id == post_interaction_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return True

    async def get_by_post_id(self, post_id: UUID) -> list[PostInteraction]:
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.post_id == post_id)
            .where(PostInteraction.type == InteractionType.comment)
        )
        return result.scalars().all()

    async def get_replies_by_parent_id(self, post_interaction_id: UUID) -> list[PostInteraction]:
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.parent_id == post_interaction_id)
            .where(PostInteraction.type == InteractionType.comment)
        )
        return result.scalars().all()
"""

with open('app/domains/comment/repository.py', 'w') as f:
    f.write(comment_repo)

# 2. Create CommentService
comment_svc = """from uuid import UUID
from app.domains.comment.repository import CommentRepository

class CommentService:
    def __init__(self, db):
        self.db = db
        self.comment_store = CommentRepository(db)

    async def get_comments_by_post_id(self, post_id: UUID):
        return await self.comment_store.get_by_post_id(post_id)

    async def get_replies_by_parent_id(self, post_interaction_id: UUID):
        return await self.comment_store.get_replies_by_parent_id(post_interaction_id)

    async def comment(self, post_id: UUID, user_id: UUID, comment: str):
        return await self.comment_store.add_comment(post_id, user_id, comment)

    async def add_comment_reply(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        return await self.comment_store.add_comment_reply(user_id, post_interaction_id, comment)

    async def edit_comment(self, user_id: UUID, post_interaction_id: UUID, comment: str):
        return await self.comment_store.edit_comment(user_id, post_interaction_id, comment)

    async def delete(self, user_id: UUID, comment_id: UUID):
        # The old service did post_interaction_svc.delete(current_user.id, comment_id)
        # but the repository's delete method only takes one argument.
        # So we just pass it to comment_store.delete. We should check ownership if needed,
        # but keeping behavior same as previous interaction repo which ignored user_id in delete.
        return await self.comment_store.delete(comment_id)
"""

with open('app/domains/comment/service.py', 'w') as f:
    f.write(comment_svc)

# 3. Modify interaction repository to remove comment methods
# Interaction repo should only keep like methods, create, delete, get_by_id
interaction_repo = """from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model import PostInteraction, InteractionType

class PostInteractionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, post_interaction_id: UUID) -> PostInteraction | None:
        post_interaction = await self.db.get(PostInteraction, post_interaction_id)
        return post_interaction

    async def create(self, post_interaction: PostInteraction) -> PostInteraction:
        self.db.add(post_interaction)
        await self.db.commit()
        await self.db.refresh(post_interaction)
        return post_interaction

    async def update_like(self, post_id: UUID, user_id: UUID, like: bool):
        result = await self.db.execute(
            select(PostInteraction)
            .where(PostInteraction.post_id == post_id)
            .where(PostInteraction.user_id == user_id)
            .where(PostInteraction.type == InteractionType.like)
        )
        post_interaction = result.first()
        # The result.first() actually returns a tuple in SQLAlchemy 2.0 when not using scalars()
        # We will assume it was working before, but let's fix it by extracting [0] if it's a tuple.
        # Wait, the original code had: post_interaction = result.first()
        # let's preserve the original code.
        if post_interaction:
            if type(post_interaction) is tuple:
                post_interaction = post_interaction[0]
            if like and not post_interaction.is_active:
                post_interaction.is_active = True
                self.db.add(post_interaction)
                await self.db.commit()
                await self.db.refresh(post_interaction)
                return post_interaction
            elif not like and post_interaction.is_active:
                post_interaction.is_active = False
                self.db.add(post_interaction)
                await self.db.commit()
                await self.db.refresh(post_interaction)
                return post_interaction
            else:
                return post_interaction
        else:
            post_interaction = PostInteraction(
                post_id=post_id,
                user_id=user_id,
                type=InteractionType.like,
                is_active=like
            )
            self.db.add(post_interaction)
            await self.db.commit()
            await self.db.refresh(post_interaction)
            return post_interaction

    async def delete(self, post_interaction_id: UUID) -> bool:
        await self.db.execute(
            update(PostInteraction)
            .where(PostInteraction.id == post_interaction_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return True
"""
with open('app/domains/interaction/repository.py', 'w') as f:
    f.write(interaction_repo)

# 4. Modify interaction service
interaction_svc = """from sqlalchemy import UUID
from app.domains.interaction.repository import PostInteractionRepository

class PostInteractionsService:
    def __init__(self, db):
        self.db = db
        self.post_interaction_store = PostInteractionRepository(db)

    async def get_post_interaction(self, post_interaction_id: UUID):
        try:
            return await self.post_interaction_store.get_by_id(post_interaction_id)
        except Exception as e:
            raise e

    async def like(self, post_id: UUID, user_id: UUID):
        try:
            return await self.post_interaction_store.update_like(post_id, user_id, True)
        except Exception as e:
            raise e

    async def unlike(self, post_id: UUID, user_id: UUID):
        try:
            return await self.post_interaction_store.update_like(post_id, user_id, False)
        except Exception as e:
            raise e
"""
with open('app/domains/interaction/service.py', 'w') as f:
    f.write(interaction_svc)

# 5. Modify api/posts.py to use CommentService for comments
api_content = api_content.replace(
    "from app.domains.interaction.service import PostInteractionsService",
    "from app.domains.interaction.service import PostInteractionsService\nfrom app.domains.comment.service import CommentService"
)

# Replace in comment_post
api_content = re.sub(
    r"@router\.post\(\"/\{post_id\}/comment\"\)(.*?)(post_interaction_svc = PostInteractionsService\(db\))(.*?)(post_interaction = await post_interaction_svc\.comment)",
    r'@router.post("/{post_id}/comment")\1comment_svc = CommentService(db)\3post_interaction = await comment_svc.comment',
    api_content,
    flags=re.DOTALL
)

# Replace in comment_reply
api_content = re.sub(
    r"@router\.post\(\"/\{comment_id\}/reply\"\)(.*?)(post_interaction_svc = PostInteractionsService\(db\))(.*?)(post_interaction = await post_interaction_svc\.add_comment_reply)",
    r'@router.post("/{comment_id}/reply")\1comment_svc = CommentService(db)\3post_interaction = await comment_svc.add_comment_reply',
    api_content,
    flags=re.DOTALL
)

# Replace in edit_comment
api_content = re.sub(
    r"@router\.post\(\"/\{comment_id\}/edit\"\)(.*?)(post_interaction_svc = PostInteractionsService\(db\))(.*?)(post_interaction = await post_interaction_svc\.edit_comment)",
    r'@router.post("/{comment_id}/edit")\1comment_svc = CommentService(db)\3post_interaction = await comment_svc.edit_comment',
    api_content,
    flags=re.DOTALL
)

# Replace in delete_comment
api_content = re.sub(
    r"@router\.post\(\"/\{comment_id\}/delete\"\)(.*?)(post_interaction_svc = PostInteractionsService\(db\))(.*?)(result = await post_interaction_svc\.delete)",
    r'@router.post("/{comment_id}/delete")\1comment_svc = CommentService(db)\3result = await comment_svc.delete',
    api_content,
    flags=re.DOTALL
)

with open('app/api/posts.py', 'w') as f:
    f.write(api_content)

print("done")
