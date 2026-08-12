import os
import glob

replacements = {
    "app.services.category": "app.domains.preference.service",
    "app.services.post_intrections": "app.domains.interaction.service",
    "app.services.post": "app.domains.post.service",
    "app.services.feed": "app.domains.feed.service",
    "app.db.repositories.post_intrection_repo": "app.domains.interaction.repository",
    "app.db.repositories.post_repo": "app.domains.post.repository",
    "app.db.repositories.category_repo": "app.domains.preference.repository",
    "app.db.repositories.feed_repo": "app.domains.feed.repository",
    "app.storage.post": "app.domains.post.storage",
    "app.storage.categories": "app.domains.preference.storage",
    "app.storage.pool": "app.domains.feed.pools.pool",
    "app.redis.post_store": "app.domains.post.redis",
    "app.redis.category_store": "app.domains.preference.redis",
    "app.redis.pool_store": "app.domains.feed.redis",
    "app.redis.client": "app.core.redis",
    "app.redis.keys": "app.core.keys",
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
