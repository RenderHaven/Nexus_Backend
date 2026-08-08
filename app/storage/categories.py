from uuid import UUID

from app.db.repositories.category_repo import CategoryRepository
from app.redis.category_store import CategoryStore
from app.schemas.schemas import Category


class CategoryStorage:

    def __init__(self, db):
        self.category_store = CategoryStore()
        self.category_repo = CategoryRepository(db)

    async def get_category(self, category_id: UUID) -> Category | None:
        category = await self.category_store.get(category_id)

        if category:
            return Category.model_validate(category)

        db_category = await self.category_repo.get_by_id(category_id)

        if not db_category:
            return None

        category = Category.model_validate(db_category)

        await self.category_store.set(
            category.id,
            category.model_dump(mode="json")
        )

        return category

    async def get_all(self) -> list[Category]:
        categories = await self.category_store.get_all_categories()

        if categories:
            return [
                Category.model_validate(category)
                for category in categories
            ]

        db_categories = await self.category_repo.get_all()

        categories = [
            Category.model_validate(category)
            for category in db_categories
        ]

        await self.category_store.set_all_categories(
            [
                category.model_dump(mode="json")
                for category in categories
            ]
        )

        for category in categories:
            await self.category_store.set_category(
                category.id,
                category.model_dump(mode="json")
            )

        return categories

    async def update_category(self, category: Category) -> Category | None:
        db_category = await self.category_repo.update(category)

        if not db_category:
            return None

        category = Category.model_validate(db_category)

        await self.category_store.set(
            category.id,
            category.model_dump(mode="json")
        )

        return category

    async def delete_category(self, category_id: UUID):
        await self.category_repo.delete(category_id)
        await self.category_store.delete(category_id)