from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()