with open("app/domains/user/repository.py", "r") as f:
    content = f.read()

update_profile_json_method = """
    async def update_profile_json(self, user_id: UUID, profile: dict) -> None:
        from sqlalchemy import update
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(profile=profile)
        )
        await self.db.commit()
"""

# append to UserRepository class
lines = content.split('\n')
for i in range(len(lines)):
    if "async def get_posts_ids" in lines[i]:
        insert_idx = i
        break

lines.insert(insert_idx, update_profile_json_method)

with open("app/domains/user/repository.py", "w") as f:
    f.write('\n'.join(lines))
