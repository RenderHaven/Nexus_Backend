with open("app/domains/user/schemas.py", "r") as f:
    content = f.read()

import_stmt = "from app.domains.user.profile_schemas import UserProfile\n"
if "from app.domains.user.profile_schemas import UserProfile" not in content:
    content = import_stmt + content

content = content.replace("profile: dict[str, Any] = Field(default_factory=dict)", "profile: UserProfile = Field(default_factory=UserProfile)")

# Remove the commented out block if it exists
import re
content = re.sub(r'# def typed_profile.*?(?=\n\S|\Z)', '', content, flags=re.DOTALL)
content = re.sub(r'def typed_profile.*?(?=\n\S|\Z)', '', content, flags=re.DOTALL)

with open("app/domains/user/schemas.py", "w") as f:
    f.write(content)
