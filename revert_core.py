import os
import glob
import shutil

os.makedirs("app/redis", exist_ok=True)
os.makedirs("app/db", exist_ok=True)

# Move redis files
if os.path.exists("app/core/redis.py"):
    shutil.move("app/core/redis.py", "app/redis/client.py")
if os.path.exists("app/core/keys.py"):
    shutil.move("app/core/keys.py", "app/redis/keys.py")

# Move db files
if os.path.exists("app/core/session.py"):
    shutil.move("app/core/session.py", "app/db/session.py")
if os.path.exists("app/core/database.py"):
    shutil.move("app/core/database.py", "app/db/database.py")

replacements = {
    "app.core.redis": "app.redis.client",
    "app.core.keys": "app.redis.keys",
    "app.core.session": "app.db.session",
    "app.core.database": "app.db.database",
}

for filepath in glob.glob("app/**/*.py", recursive=True):
    with open(filepath, "r") as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        print(f"Updating {filepath}")
        with open(filepath, "w") as f:
            f.write(new_content)
