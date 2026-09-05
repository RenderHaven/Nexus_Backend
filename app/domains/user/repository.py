from uuid import UUID
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import College, Post, User


class UserRepository:
    """
    Reads of the `users` table and nothing else.

    No relationship is eager loaded here. college, interests, open_to and
    badges used to be pulled on every single user fetch -- including the one
    behind every login -- and no schema in the codebase reads any of them:
    UserMini, UserBasic, User and UserAdminRow are all scalar columns plus the
    profile JSONB. Anything that does need a person's college resolves
    college_id against college:{id}, the same way a post does.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Bulk / index reads
    #
    # A narrower column list still, for callers walking the whole table. Note
    # that nothing here may be written to user:{id}: a projection cached under
    # that key would make the next UserBasic read validate successfully
    # against an incomplete blob and quietly fill in defaults.
    # ------------------------------------------------------------------

    def _flat_select(self):
        return select(
            User.id,
            User.username,
            User.college_id,
            User.role,
            User.is_alumni,
            User.is_active,
            User.created_at,
        )

    async def get_user_row(self, user_id: UUID):
        result = await self.db.execute(
            self._flat_select().where(User.id == user_id)
        )
        return result.one_or_none()

    async def get_all_users(
        self,
        after: tuple | None = None,
        limit: int = 1000,
        is_active: bool | None = None,
    ) -> list:
        """
        One keyset page of every user, ordered by (created_at, id).

        Pass is_active=True for only the accounts still in service -- that is
        what the search rebuild does, so a reindex cannot put a deactivated
        person back into the index.
        """
        query = (
            self._flat_select()
            .order_by(User.created_at, User.id)
            .limit(limit)
        )

        if is_active is not None:
            query = query.where(User.is_active.is_(is_active))

        if after is not None:
            query = query.where(tuple_(User.created_at, User.id) > after)

        return list((await self.db.execute(query)).all())

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def college_exists(self, college_id: UUID) -> bool:
        result = await self.db.execute(
            select(College.id).where(College.id == college_id)
        )
        return result.scalar_one_or_none() is not None

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # Admin table
    # ------------------------------------------------------------------

    # Sortable columns. The caller sends a key, never a column name, so
    # nothing user-supplied reaches the ORDER BY.
    _LIST_SORTS = {
        "created_at": User.created_at,
        "username": User.username,
        "role": User.role,
        "total_xp": User.total_xp,
    }

    async def list_users(
        self,
        limit: int = 20,
        offset: int = 0,
        college_id: UUID | None = None,
        role=None,
        is_alumni: bool | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> list[User]:
        """
        One page of the admin user table.

        college_id here is already the scoped value -- the service decides it
        from the caller, so a moderator's request can only ever name their own
        college by the time it reaches this method.
        """
        conditions = []

        if college_id is not None:
            conditions.append(User.college_id == college_id)

        if role is not None:
            conditions.append(User.role == role)

        if is_alumni is not None:
            conditions.append(User.is_alumni.is_(is_alumni))

        if is_active is not None:
            conditions.append(User.is_active.is_(is_active))

        if q:
            # escape the LIKE wildcards so a literal % typed into a search box
            # does not turn into "match everything".
            term = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{term}%"
            conditions.append(
                or_(
                    User.username.ilike(pattern, escape="\\"),
                    User.email.ilike(pattern, escape="\\"),
                )
            )

        column = self._LIST_SORTS.get(sort, User.created_at)
        direction = (
            (lambda c: c.desc()) if order == "desc" else (lambda c: c.asc())
        )

        result = await self.db.execute(
            select(User)
            .where(*conditions)
            .order_by(direction(column), direction(User.id))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def users_by_ids(self, user_ids: list[UUID]) -> list[User]:
        if not user_ids:
            return []
        result = await self.db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        return list(result.scalars().all())

    async def update_fields(self, user_id: UUID, changes: dict) -> UUID | None:
        """Partial column update. Only the keys given are touched."""
        if not changes:
            return user_id

        from sqlalchemy import update

        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**changes)
            .returning(User.id)
        )
        updated = result.scalar_one_or_none()

        await self.db.commit()
        return updated

    async def set_active(self, user_id: UUID, is_active: bool) -> UUID | None:
        return await self.update_fields(user_id, {"is_active": is_active})

    async def set_active_bulk(
        self,
        user_ids: list[UUID],
        is_active: bool,
    ) -> list[UUID]:
        if not user_ids:
            return []

        from sqlalchemy import update

        result = await self.db.execute(
            update(User)
            .where(User.id.in_(user_ids))
            .values(is_active=is_active)
            .returning(User.id)
        )
        updated = list(result.scalars().all())

        await self.db.commit()
        return updated

    async def set_password(self, user_id: UUID, hashed: str) -> UUID | None:
        return await self.update_fields(user_id, {"password": hashed})

    async def content_counts(self, user_id: UUID) -> dict[str, int]:
        """
        How much this person has written. A hard delete is refused when any
        of it exists, because most of the tables pointing at users.id have no
        cascade and the delete would fail on a foreign key anyway.
        """
        from app.db.models import PostComment, PostReaction

        counts = {}

        for key, model in (
            ("posts", Post),
            ("comments", PostComment),
            ("reactions", PostReaction),
        ):
            result = await self.db.execute(
                select(func.count(model.id)).where(model.user_id == user_id)
            )
            counts[key] = result.scalar_one() or 0

        return counts


    async def update_profile_json(self, user_id: UUID, profile: dict) -> None:
        from sqlalchemy import update
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(profile=profile)
        )
        await self.db.commit()

    async def get_posts_ids(self,user_id:UUID,limit:int)->list[Post]:
        result=await self.db.execute(
            select(Post)
            .where(Post.user_id == user_id)
            .where(Post.is_active.is_(True))
            .order_by(Post.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

