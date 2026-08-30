from app.domains.user.profile_schemas import UserProfile

raw = {
    "about": "Hello",
    "skills": ["Python"]
}

p = UserProfile.model_validate(raw)
print(p.model_dump(mode="json"))
