from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    # Optional: with no cluster configured the app still boots and every
    # non-search route works, so search can be added per environment.
    OPENSEARCH_URL: str | None = None
    OPENSEARCH_INDEX_PREFIX: str = ""
    OPENSEARCH_VERIFY_CERTS: bool = True
    OPENSEARCH_TIMEOUT: int = 10

    KAFKA_BOOTSTRAP_SERVERS: str | None = None
    KAFKA_INTERACTIONS_TOPIC: str = "interactions_topic"
    KAFKA_COMMENTS_TOPIC: str = "comments_topic"

    REDIS_REBUILD_INTERVAL: str = "6h"
    DB_ECHO: bool = False

    CURSOR_SECRET_KEY: str
    SECRET_KEY: str

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Limits on what a user may submit with a post.
    # MAX_TITLE_LENGTH must stay within the posts.title column (varchar 255).
    MAX_TITLE_LENGTH: int = 255
    MAX_BODY_LENGTH: int = 5000
    MAX_MEDIA_COUNT: int = 10
    MAX_MEDIA_SIZE: int = 10 * 1024 * 1024

    # Limits on what a user may put in their profile.
    # Where media lives in Cloudinary. Every folder below is nested under
    # MEDIA_BASE_DIR, and only these folders may ever be written to.
    MEDIA_BASE_DIR: str = "nexus_media"
    POST_MEDIA_DIR: str = "posts"
    DELETED_POST_MEDIA_DIR: str = "deleted_posts"
    PROFILE_MEDIA_DIR: str = "profiles"
    OTHER_MEDIA_DIR: str = "other"

    # Largest batch of ids any /batch endpoint will accept.
    MAX_BATCH_SIZE: int = 15

    MAX_USERNAME_LENGTH: int = 100
    MAX_ABOUT_LENGTH: int = 2000
    MAX_SKILLS: int = 50
    MAX_PROFILE_ITEMS: int = 25
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()