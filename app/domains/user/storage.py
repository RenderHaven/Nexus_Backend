from uuid import UUID

from app.domains.user.repository import UserRepository
from app.domains.user.redis import UserRedisStore
from app.domains.user.schemas import User, UserBasic, UserMini
from app.redis import metrics


class UserStorage:

    def __init__(self, db, user_repo: UserRepository):
        self.db = db
        self.user_redis_store = UserRedisStore()
        self.user_repo = user_repo

    async def get_author(self, user_id: UUID) -> UserMini | None:
        """
        One person, in the smallest shape a reference needs.

        Projected from what is cached under user:{id}, never stored
        separately: UserMini is a narrower view of the same blob, and
        model_validate drops the keys it does not declare.
        """
        user = await self.get_user(user_id)
        if not user:
            return None
        return UserMini.model_validate(user.model_dump(mode="json"))

    async def get_authors(self, user_ids: list[UUID]) -> dict[UUID, UserBasic]:
        """
        Resolve a batch of user ids for hydrating a list.

        One MGET, then one WHERE id IN (...) for whatever missed, then a
        backfill of the same user:{id} key the single read uses. Full ORM
        rows on the fallback, never a column projection -- see the note on
        get_authors' contract in the entity-hydration design: a narrow write
        to user:{id} would make the next UserBasic read succeed against an
        incomplete blob instead of failing.

        Returns UserBasic, the one shape that lives under user:{id}. A
        consumer whose field is declared UserMini gets the narrow view for
        free -- UserBasic is a subclass, so the declared type decides what is
        serialised.
        """
        if not user_ids:
            return {}

        unique_ids = list(dict.fromkeys(user_ids))
        cached = await self.user_redis_store.get_many(unique_ids)

        result: dict[UUID, UserBasic] = {}
        missing: list[UUID] = []

        for user_id, data in zip(unique_ids, cached):
            if data:
                result[user_id] = UserBasic.model_validate(data)
            else:
                missing.append(user_id)

        await metrics.record("user", hits=len(result), misses=len(missing))

        if missing:
            db_users = await self.user_repo.users_by_ids(missing)

            to_cache = []
            for db_user in db_users:
                user_basic = UserBasic.model_validate(db_user)
                result[db_user.id] = user_basic
                to_cache.append(user_basic.model_dump(mode="json"))

            await self.user_redis_store.set_many(to_cache)

        return result

    async def get_user(self, user_id: UUID) -> UserBasic | None:
        user_data = await self.user_redis_store.get(user_id)
        if user_data:
            await metrics.record("user", hits=1)
            return UserBasic.model_validate(user_data)

        await metrics.record("user", misses=1)

        db_user = await self.user_repo.get_by_id(user_id)
        if not db_user:
            return None

        user_basic = UserBasic.model_validate(db_user)
        await self.user_redis_store.set(user_id, user_basic.model_dump(mode="json"))
        return user_basic

    async def get_profile(self, user_id: UUID) -> User | None:
        profile_data = await self.user_redis_store.get_profile(user_id)
        if profile_data:
            await metrics.record("user_profile", hits=1)
            return User.model_validate(profile_data)

        await metrics.record("user_profile", misses=1)

        db_user = await self.user_repo.get_by_id(user_id)
        if not db_user:
            return None

        user_profile = User.model_validate(db_user)
        await self.user_redis_store.set_profile(
            user_id, user_profile.model_dump(mode="json")
        )
        return user_profile

    async def get_category_preferences(self, user_id: UUID) -> dict[str, float] | None:
        # TODO: real preferences; the feed falls back todefaults until then.
        return {}
