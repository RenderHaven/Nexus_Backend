from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.model import User, UserInterest, UserOpenTo, UserBadge


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _user_options(self):
        return [
            selectinload(User.college),
            selectinload(User.interests).selectinload(UserInterest.category),
            selectinload(User.open_to),
            selectinload(User.badges).selectinload(UserBadge.badge),
        ]

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(*self._user_options())
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(*self._user_options())
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(*self._user_options())
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

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

    async def list_users(self, limit: int = 20, offset: int = 0) -> list[User]:
        result = await self.db.execute(
            select(User)
            .options(*self._user_options())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
